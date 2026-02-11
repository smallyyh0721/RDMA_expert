---
title: "RDMA Connection Manager (RDMA-CM) Programming Manual"
category: manuals
tags:
  - rdma
  - rdma-cm
  - rdmacm
  - librdmacm
  - connection_management
  - rdma_connect
  - rdma_accept
  - rdma_listen
  - event_channel
  - client_server
  - address_resolution
  - route_resolution
source: "librdmacm API documentation, RDMA-CM programming guide, kernel rdma_cm interface"
---

# RDMA Connection Manager (RDMA-CM) Programming Manual

## 1. Introduction to RDMA-CM

The RDMA Connection Manager (RDMA-CM) library (`librdmacm`) provides a transport-neutral interface for establishing RDMA connections. It abstracts the complexities of address resolution, route resolution, and QP state transitions, providing a socket-like programming model for RDMA applications.

### 1.1 Why RDMA-CM?

Without RDMA-CM, establishing an RDMA connection requires:

1. Out-of-band exchange of QP numbers, LIDs/GIDs, PSNs, and memory keys (typically via TCP sockets).
2. Manual QP state transitions (RESET -> INIT -> RTR -> RTS).
3. Manual GID/LID resolution for the destination.

RDMA-CM automates all of this, providing:

- Address resolution (IP to GID/LID mapping)
- Route resolution (path computation)
- Automatic QP state transitions
- Connection establishment and teardown
- Multicast group management
- Event-driven notification model

### 1.2 Headers and Linking

```c
#include <rdma/rdma_cma.h>
#include <rdma/rdma_verbs.h>   /* Optional: helper verbs */

/* Link with: -lrdmacm -libverbs */
```

### 1.3 Architecture Overview

```
Application
    |
    v
+-------------------+
| librdmacm         |  User-space RDMA-CM library
+-------------------+
    |
    v
+-------------------+
| /dev/rdma_cm      |  Character device
+-------------------+
    |
    v
+-------------------+
| rdma_cm (kernel)  |  Kernel connection manager
+-------------------+
    |
    +---> IB CM (for InfiniBand)
    +---> iWARP CM (for iWARP)
    +---> (RoCE uses IB CM over Ethernet)
```

---

## 2. Core Data Structures

### 2.1 rdma_cm_id

The `rdma_cm_id` is the central abstraction, analogous to a socket file descriptor.

```c
struct rdma_cm_id {
    struct ibv_context      *verbs;         /* Device context */
    struct rdma_event_channel *channel;     /* Event channel */
    void                    *context;       /* User context */
    struct ibv_qp           *qp;           /* Associated QP */
    struct rdma_route        route;         /* Resolved route info */
    enum rdma_port_space     ps;           /* Port space (TCP/UDP) */
    uint8_t                  port_num;     /* Local port number */
    struct rdma_cm_event    *event;         /* For inline event usage */
    struct ibv_comp_channel *send_cq_channel;
    struct ibv_cq           *send_cq;
    struct ibv_comp_channel *recv_cq_channel;
    struct ibv_cq           *recv_cq;
    struct ibv_srq          *srq;
    struct ibv_pd           *pd;
    enum ibv_qp_type         qp_type;
};
```

### 2.2 rdma_cm_event

Events are the mechanism for reporting connection state changes.

```c
struct rdma_cm_event {
    struct rdma_cm_id       *id;           /* CM ID for this event */
    struct rdma_cm_id       *listen_id;    /* Listener CM ID (server) */
    enum rdma_cm_event_type  event;        /* Event type */
    int                      status;       /* Event status (0 = success) */
    union {
        struct rdma_conn_param conn;       /* Connection parameters */
        struct rdma_ud_param   ud;         /* UD parameters */
    } param;
};
```

### 2.3 Event Types

| Event | Description | Triggered By |
|-------|-------------|--------------|
| RDMA_CM_EVENT_ADDR_RESOLVED | Address resolution completed | rdma_resolve_addr |
| RDMA_CM_EVENT_ADDR_ERROR | Address resolution failed | rdma_resolve_addr |
| RDMA_CM_EVENT_ROUTE_RESOLVED | Route resolution completed | rdma_resolve_route |
| RDMA_CM_EVENT_ROUTE_ERROR | Route resolution failed | rdma_resolve_route |
| RDMA_CM_EVENT_CONNECT_REQUEST | Incoming connection request | Remote rdma_connect |
| RDMA_CM_EVENT_CONNECT_RESPONSE | Connection response (unreliable) | rdma_connect |
| RDMA_CM_EVENT_CONNECT_ERROR | Connection error | rdma_connect/accept |
| RDMA_CM_EVENT_UNREACHABLE | Remote unreachable | rdma_connect |
| RDMA_CM_EVENT_REJECTED | Connection rejected | rdma_reject |
| RDMA_CM_EVENT_ESTABLISHED | Connection established | rdma_accept |
| RDMA_CM_EVENT_DISCONNECTED | Connection disconnected | rdma_disconnect |
| RDMA_CM_EVENT_DEVICE_REMOVAL | Device removed | System event |
| RDMA_CM_EVENT_MULTICAST_JOIN | Multicast join completed | rdma_join_multicast |
| RDMA_CM_EVENT_MULTICAST_ERROR | Multicast error | System event |
| RDMA_CM_EVENT_ADDR_CHANGE | Address changed | System event |
| RDMA_CM_EVENT_TIMEWAIT_EXIT | Connection timewait expired | Timer |

---

## 3. Event Channel Operations

### 3.1 rdma_create_event_channel

```c
struct rdma_event_channel *rdma_create_event_channel(void);
```

Creates an event channel for receiving CM events. The channel contains a file descriptor (`channel->fd`) that can be used with `poll()`, `select()`, or `epoll()`.

**Return Value:** Event channel pointer on success, NULL on failure (check errno).

```c
struct rdma_event_channel *ec = rdma_create_event_channel();
if (!ec) {
    fprintf(stderr, "Failed to create event channel: %s\n", strerror(errno));
    return -1;
}

/* For non-blocking operation: */
int flags = fcntl(ec->fd, F_GETFL);
fcntl(ec->fd, F_SETFL, flags | O_NONBLOCK);
```

### 3.2 rdma_destroy_event_channel

```c
void rdma_destroy_event_channel(struct rdma_event_channel *channel);
```

Destroys the event channel. All `rdma_cm_id`s associated with the channel must be destroyed first.

---

## 4. CM ID Lifecycle

### 4.1 rdma_create_id

```c
int rdma_create_id(struct rdma_event_channel *channel,
                   struct rdma_cm_id **id, void *context,
                   enum rdma_port_space ps);
```

Creates a new CM identifier, analogous to `socket()`.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| channel | struct rdma_event_channel* | Event channel for notifications |
| id | struct rdma_cm_id** | Output: new CM ID |
| context | void* | User context stored in id->context |
| ps | enum rdma_port_space | RDMA_PS_TCP (reliable) or RDMA_PS_UDP (unreliable) |

**Port Spaces:**

| Port Space | Description | QP Type |
|------------|-------------|---------|
| RDMA_PS_TCP | Reliable stream (RC) | IBV_QPT_RC |
| RDMA_PS_UDP | Unreliable datagram (UD) | IBV_QPT_UD |
| RDMA_PS_IB | InfiniBand native | Any |

**Example:**

```c
struct rdma_cm_id *cm_id;
int ret = rdma_create_id(ec, &cm_id, NULL, RDMA_PS_TCP);
if (ret) {
    fprintf(stderr, "Failed to create CM ID: %s\n", strerror(errno));
    return -1;
}
```

### 4.2 rdma_destroy_id

```c
int rdma_destroy_id(struct rdma_cm_id *id);
```

Destroys a CM ID and frees all associated resources. If a QP was created with `rdma_create_qp()`, it is automatically destroyed.

---

## 5. Address and Route Resolution

### 5.1 rdma_resolve_addr

```c
int rdma_resolve_addr(struct rdma_cm_id *id,
                      struct sockaddr *src_addr,
                      struct sockaddr *dst_addr,
                      int timeout_ms);
```

Resolves a destination address to an RDMA device and port. This maps an IP address to the appropriate RDMA device, GID, and (for IB) LID.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | struct rdma_cm_id* | CM ID to resolve |
| src_addr | struct sockaddr* | Local address (NULL for automatic selection) |
| dst_addr | struct sockaddr* | Remote address to resolve |
| timeout_ms | int | Timeout in milliseconds |

**Result Event:** RDMA_CM_EVENT_ADDR_RESOLVED or RDMA_CM_EVENT_ADDR_ERROR

**Example:**

```c
struct sockaddr_in dst_addr;
memset(&dst_addr, 0, sizeof(dst_addr));
dst_addr.sin_family = AF_INET;
dst_addr.sin_port = htons(20000);
inet_pton(AF_INET, "192.168.1.100", &dst_addr.sin_addr);

int ret = rdma_resolve_addr(cm_id, NULL, (struct sockaddr *)&dst_addr, 2000);
if (ret) {
    fprintf(stderr, "rdma_resolve_addr failed: %s\n", strerror(errno));
    return -1;
}

/* Wait for RDMA_CM_EVENT_ADDR_RESOLVED */
```

After address resolution, `cm_id->verbs` is set to the device context and `cm_id->port_num` is set.

### 5.2 rdma_resolve_route

```c
int rdma_resolve_route(struct rdma_cm_id *id, int timeout_ms);
```

Resolves the route to the destination. For InfiniBand, this involves path record lookups via the Subnet Administrator. For RoCE/Ethernet, route resolution uses the IP routing table.

Must be called after address resolution completes.

**Result Event:** RDMA_CM_EVENT_ROUTE_RESOLVED or RDMA_CM_EVENT_ROUTE_ERROR

**Example:**

```c
ret = rdma_resolve_route(cm_id, 2000);
if (ret) {
    fprintf(stderr, "rdma_resolve_route failed: %s\n", strerror(errno));
    return -1;
}

/* Wait for RDMA_CM_EVENT_ROUTE_RESOLVED */
```

After route resolution, `cm_id->route` contains the resolved path information.

---

## 6. Connection Establishment

### 6.1 Server Side

#### 6.1.1 rdma_bind_addr

```c
int rdma_bind_addr(struct rdma_cm_id *id, struct sockaddr *addr);
```

Binds the CM ID to a local address, analogous to `bind()`. Specifying a specific IP selects the RDMA device; using INADDR_ANY allows connections on any RDMA device.

```c
struct sockaddr_in addr;
memset(&addr, 0, sizeof(addr));
addr.sin_family = AF_INET;
addr.sin_port = htons(20000);
addr.sin_addr.s_addr = INADDR_ANY;

ret = rdma_bind_addr(cm_id, (struct sockaddr *)&addr);
if (ret) {
    fprintf(stderr, "rdma_bind_addr failed: %s\n", strerror(errno));
    return -1;
}
```

#### 6.1.2 rdma_listen

```c
int rdma_listen(struct rdma_cm_id *id, int backlog);
```

Begins listening for incoming connections, analogous to `listen()`.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | struct rdma_cm_id* | Listening CM ID |
| backlog | int | Maximum pending connections |

```c
ret = rdma_listen(cm_id, 10);
if (ret) {
    fprintf(stderr, "rdma_listen failed: %s\n", strerror(errno));
    return -1;
}
printf("Listening on port %d\n", ntohs(rdma_get_src_port(cm_id)));
```

#### 6.1.3 rdma_accept

```c
int rdma_accept(struct rdma_cm_id *id,
                struct rdma_conn_param *conn_param);
```

Accepts an incoming connection request. Called on the new CM ID received in the RDMA_CM_EVENT_CONNECT_REQUEST event.

**rdma_conn_param fields:**

| Field | Type | Description |
|-------|------|-------------|
| private_data | const void* | User data sent to peer (up to 196 bytes for IB) |
| private_data_len | uint8_t | Length of private data |
| responder_resources | uint8_t | Max outstanding RDMA Read/Atomic as responder |
| initiator_depth | uint8_t | Max outstanding RDMA Read/Atomic as initiator |
| flow_control | uint8_t | Flow control (usually 1) |
| retry_count | uint8_t | Retry count (0-7) |
| rnr_retry_count | uint8_t | RNR retry count (0-7, 7=infinite) |

```c
struct rdma_conn_param conn_param = {
    .responder_resources = 16,
    .initiator_depth = 16,
    .rnr_retry_count = 7,
};

ret = rdma_accept(new_cm_id, &conn_param);
if (ret) {
    fprintf(stderr, "rdma_accept failed: %s\n", strerror(errno));
    return -1;
}
```

#### 6.1.4 rdma_reject

```c
int rdma_reject(struct rdma_cm_id *id, const void *private_data,
                uint8_t private_data_len);
```

Rejects an incoming connection request. Optional private data explains the rejection reason to the client.

```c
const char *reason = "Server busy";
rdma_reject(new_cm_id, reason, strlen(reason) + 1);
```

### 6.2 Client Side

#### 6.2.1 rdma_connect

```c
int rdma_connect(struct rdma_cm_id *id,
                 struct rdma_conn_param *conn_param);
```

Initiates a connection to the remote server. Must be called after route resolution completes and a QP has been created.

```c
struct rdma_conn_param conn_param = {
    .responder_resources = 16,
    .initiator_depth = 16,
    .retry_count = 7,
    .rnr_retry_count = 7,
};

ret = rdma_connect(cm_id, &conn_param);
if (ret) {
    fprintf(stderr, "rdma_connect failed: %s\n", strerror(errno));
    return -1;
}

/* Wait for RDMA_CM_EVENT_ESTABLISHED */
```

---

## 7. Event Processing

### 7.1 rdma_get_cm_event

```c
int rdma_get_cm_event(struct rdma_event_channel *channel,
                      struct rdma_cm_event **event);
```

Retrieves the next CM event from the event channel. This is a blocking call by default. For non-blocking behavior, set O_NONBLOCK on `channel->fd`.

**Return Value:** 0 on success, -1 on failure (check errno). With non-blocking mode, returns -1 with errno=EAGAIN if no event available.

```c
struct rdma_cm_event *event;
ret = rdma_get_cm_event(ec, &event);
if (ret) {
    fprintf(stderr, "rdma_get_cm_event failed: %s\n", strerror(errno));
    return -1;
}

printf("Event: %s, status: %d\n",
       rdma_event_str(event->event), event->status);

/* Process event based on type */
switch (event->event) {
case RDMA_CM_EVENT_ADDR_RESOLVED:
    /* Proceed with route resolution */
    break;
case RDMA_CM_EVENT_ROUTE_RESOLVED:
    /* Create QP and connect */
    break;
case RDMA_CM_EVENT_CONNECT_REQUEST:
    /* Server: new connection request */
    break;
case RDMA_CM_EVENT_ESTABLISHED:
    /* Connection established */
    break;
case RDMA_CM_EVENT_DISCONNECTED:
    /* Peer disconnected */
    break;
case RDMA_CM_EVENT_REJECTED:
    fprintf(stderr, "Connection rejected: status=%d\n", event->status);
    if (event->param.conn.private_data_len > 0) {
        fprintf(stderr, "Reason: %s\n",
                (char *)event->param.conn.private_data);
    }
    break;
default:
    fprintf(stderr, "Unexpected event: %s\n",
            rdma_event_str(event->event));
}

/* MUST acknowledge every event */
rdma_ack_cm_event(event);
```

### 7.2 rdma_ack_cm_event

```c
int rdma_ack_cm_event(struct rdma_cm_event *event);
```

Acknowledges a CM event, freeing its resources. Every event retrieved with `rdma_get_cm_event` MUST be acknowledged. Failing to acknowledge events causes resource leaks and eventually hangs the event channel.

**Critical Rule:** You must copy any data from the event (private_data, CM ID pointer, etc.) before acknowledging, as the event memory is freed.

```c
/* Copy data BEFORE acknowledging */
struct rdma_cm_id *new_id = event->id;
uint32_t private_data_value;
if (event->param.conn.private_data_len >= sizeof(uint32_t)) {
    memcpy(&private_data_value, event->param.conn.private_data,
           sizeof(uint32_t));
}

/* NOW acknowledge */
rdma_ack_cm_event(event);

/* Safe to use new_id and private_data_value */
```

---

## 8. QP Creation with RDMA-CM

### 8.1 rdma_create_qp

```c
int rdma_create_qp(struct rdma_cm_id *id, struct ibv_pd *pd,
                   struct ibv_qp_init_attr *qp_init_attr);
```

Creates a QP and associates it with the CM ID. The CM will automatically transition the QP through the required states during connection establishment.

```c
struct ibv_qp_init_attr qp_attr = {
    .send_cq = cq,
    .recv_cq = cq,
    .cap = {
        .max_send_wr = 128,
        .max_recv_wr = 128,
        .max_send_sge = 1,
        .max_recv_sge = 1,
        .max_inline_data = 64,
    },
    .qp_type = IBV_QPT_RC,
    .sq_sig_all = 0,
};

ret = rdma_create_qp(cm_id, pd, &qp_attr);
if (ret) {
    fprintf(stderr, "rdma_create_qp failed: %s\n", strerror(errno));
    return -1;
}
/* cm_id->qp is now set */
```

**Note:** When using `rdma_create_qp`, the QP state transitions are managed automatically:
- `rdma_connect` transitions the QP to RTS
- `rdma_accept` transitions the QP to RTS
- `rdma_disconnect` does NOT reset the QP (you must destroy it)

### 8.2 rdma_destroy_qp

```c
void rdma_destroy_qp(struct rdma_cm_id *id);
```

Destroys the QP associated with the CM ID.

---

## 9. Disconnection

### 9.1 rdma_disconnect

```c
int rdma_disconnect(struct rdma_cm_id *id);
```

Initiates a graceful disconnect. Both sides receive RDMA_CM_EVENT_DISCONNECTED.

```c
ret = rdma_disconnect(cm_id);
if (ret) {
    fprintf(stderr, "rdma_disconnect failed: %s\n", strerror(errno));
}
/* Wait for RDMA_CM_EVENT_DISCONNECTED */
```

---

## 10. Complete Client-Server Patterns

### 10.1 Connection Flow Diagram (Text)

**Client Side:**

```
rdma_create_event_channel()
rdma_create_id()
rdma_resolve_addr()
    |
    v
[RDMA_CM_EVENT_ADDR_RESOLVED]
rdma_resolve_route()
    |
    v
[RDMA_CM_EVENT_ROUTE_RESOLVED]
ibv_alloc_pd() / ibv_create_cq() / ibv_reg_mr()
rdma_create_qp()
ibv_post_recv()        <-- Post receives BEFORE connecting
rdma_connect()
    |
    v
[RDMA_CM_EVENT_ESTABLISHED]
    |
    v
--- Data Transfer Phase ---
    |
    v
rdma_disconnect()
    |
    v
[RDMA_CM_EVENT_DISCONNECTED]
Cleanup resources
```

**Server Side:**

```
rdma_create_event_channel()
rdma_create_id()
rdma_bind_addr()
rdma_listen()
    |
    v
[RDMA_CM_EVENT_CONNECT_REQUEST]  (new cm_id in event->id)
ibv_alloc_pd() / ibv_create_cq() / ibv_reg_mr()
rdma_create_qp(new_cm_id, ...)
ibv_post_recv()        <-- Post receives BEFORE accepting
rdma_accept(new_cm_id, ...)
    |
    v
[RDMA_CM_EVENT_ESTABLISHED]
    |
    v
--- Data Transfer Phase ---
    |
    v
[RDMA_CM_EVENT_DISCONNECTED]
Cleanup resources for new_cm_id
```

### 10.2 Complete Server Example

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <rdma/rdma_cma.h>
#include <infiniband/verbs.h>

#define BUF_SIZE 4096
#define PORT 20000

struct connection {
    struct rdma_cm_id *id;
    struct ibv_pd *pd;
    struct ibv_cq *cq;
    struct ibv_mr *mr;
    char *buf;
};

struct connection *create_connection(struct rdma_cm_id *id) {
    struct connection *conn = calloc(1, sizeof(*conn));
    conn->id = id;
    id->context = conn;

    /* Allocate PD using the device from the CM ID */
    conn->pd = ibv_alloc_pd(id->verbs);
    if (!conn->pd) {
        fprintf(stderr, "ibv_alloc_pd failed\n");
        free(conn);
        return NULL;
    }

    /* Create CQ */
    conn->cq = ibv_create_cq(id->verbs, 64, NULL, NULL, 0);
    if (!conn->cq) {
        fprintf(stderr, "ibv_create_cq failed\n");
        ibv_dealloc_pd(conn->pd);
        free(conn);
        return NULL;
    }

    /* Allocate and register buffer */
    conn->buf = malloc(BUF_SIZE);
    memset(conn->buf, 0, BUF_SIZE);
    conn->mr = ibv_reg_mr(conn->pd, conn->buf, BUF_SIZE,
                           IBV_ACCESS_LOCAL_WRITE |
                           IBV_ACCESS_REMOTE_WRITE |
                           IBV_ACCESS_REMOTE_READ);
    if (!conn->mr) {
        fprintf(stderr, "ibv_reg_mr failed\n");
        ibv_destroy_cq(conn->cq);
        ibv_dealloc_pd(conn->pd);
        free(conn->buf);
        free(conn);
        return NULL;
    }

    /* Create QP */
    struct ibv_qp_init_attr qp_attr = {
        .send_cq = conn->cq,
        .recv_cq = conn->cq,
        .cap = {
            .max_send_wr = 32,
            .max_recv_wr = 32,
            .max_send_sge = 1,
            .max_recv_sge = 1,
        },
        .qp_type = IBV_QPT_RC,
    };
    if (rdma_create_qp(id, conn->pd, &qp_attr)) {
        fprintf(stderr, "rdma_create_qp failed\n");
        ibv_dereg_mr(conn->mr);
        ibv_destroy_cq(conn->cq);
        ibv_dealloc_pd(conn->pd);
        free(conn->buf);
        free(conn);
        return NULL;
    }

    return conn;
}

void destroy_connection(struct connection *conn) {
    rdma_destroy_qp(conn->id);
    ibv_dereg_mr(conn->mr);
    ibv_destroy_cq(conn->cq);
    ibv_dealloc_pd(conn->pd);
    free(conn->buf);
    rdma_destroy_id(conn->id);
    free(conn);
}

int post_receive(struct connection *conn) {
    struct ibv_sge sge = {
        .addr = (uintptr_t)conn->buf,
        .length = BUF_SIZE,
        .lkey = conn->mr->lkey,
    };
    struct ibv_recv_wr wr = {
        .wr_id = (uintptr_t)conn,
        .sg_list = &sge,
        .num_sge = 1,
    };
    struct ibv_recv_wr *bad_wr;
    return ibv_post_recv(conn->id->qp, &wr, &bad_wr);
}

int main() {
    struct rdma_event_channel *ec = rdma_create_event_channel();
    if (!ec) { perror("rdma_create_event_channel"); return 1; }

    struct rdma_cm_id *listener;
    if (rdma_create_id(ec, &listener, NULL, RDMA_PS_TCP)) {
        perror("rdma_create_id"); return 1;
    }

    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(PORT),
        .sin_addr.s_addr = INADDR_ANY,
    };

    if (rdma_bind_addr(listener, (struct sockaddr *)&addr)) {
        perror("rdma_bind_addr"); return 1;
    }

    if (rdma_listen(listener, 10)) {
        perror("rdma_listen"); return 1;
    }
    printf("Server listening on port %d\n", PORT);

    /* Event loop */
    struct rdma_cm_event *event;
    while (rdma_get_cm_event(ec, &event) == 0) {
        struct rdma_cm_event event_copy = *event;
        rdma_ack_cm_event(event);

        switch (event_copy.event) {
        case RDMA_CM_EVENT_CONNECT_REQUEST: {
            printf("Connection request received\n");
            struct connection *conn = create_connection(event_copy.id);
            if (!conn) break;

            /* Post receive before accepting */
            post_receive(conn);

            struct rdma_conn_param param = {
                .responder_resources = 16,
                .initiator_depth = 16,
                .rnr_retry_count = 7,
            };
            rdma_accept(event_copy.id, &param);
            break;
        }
        case RDMA_CM_EVENT_ESTABLISHED:
            printf("Connection established\n");
            break;

        case RDMA_CM_EVENT_DISCONNECTED: {
            printf("Disconnected\n");
            struct connection *conn = event_copy.id->context;
            destroy_connection(conn);
            break;
        }
        default:
            printf("Event: %s\n", rdma_event_str(event_copy.event));
        }
    }

    rdma_destroy_id(listener);
    rdma_destroy_event_channel(ec);
    return 0;
}
```

### 10.3 Complete Client Example

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <rdma/rdma_cma.h>
#include <infiniband/verbs.h>

#define BUF_SIZE 4096

int main(int argc, char *argv[]) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <server_ip> <port>\n", argv[0]);
        return 1;
    }

    struct rdma_event_channel *ec = rdma_create_event_channel();
    struct rdma_cm_id *cm_id;
    rdma_create_id(ec, &cm_id, NULL, RDMA_PS_TCP);

    /* Resolve address */
    struct sockaddr_in dst = {
        .sin_family = AF_INET,
        .sin_port = htons(atoi(argv[2])),
    };
    inet_pton(AF_INET, argv[1], &dst.sin_addr);
    rdma_resolve_addr(cm_id, NULL, (struct sockaddr *)&dst, 2000);

    /* Wait for address resolved */
    struct rdma_cm_event *event;
    rdma_get_cm_event(ec, &event);
    if (event->event != RDMA_CM_EVENT_ADDR_RESOLVED) {
        fprintf(stderr, "Expected ADDR_RESOLVED, got %s\n",
                rdma_event_str(event->event));
        return 1;
    }
    rdma_ack_cm_event(event);

    /* Resolve route */
    rdma_resolve_route(cm_id, 2000);
    rdma_get_cm_event(ec, &event);
    if (event->event != RDMA_CM_EVENT_ROUTE_RESOLVED) {
        fprintf(stderr, "Expected ROUTE_RESOLVED, got %s\n",
                rdma_event_str(event->event));
        return 1;
    }
    rdma_ack_cm_event(event);

    /* Create resources */
    struct ibv_pd *pd = ibv_alloc_pd(cm_id->verbs);
    struct ibv_cq *cq = ibv_create_cq(cm_id->verbs, 64, NULL, NULL, 0);

    char *buf = malloc(BUF_SIZE);
    memset(buf, 0, BUF_SIZE);
    struct ibv_mr *mr = ibv_reg_mr(pd, buf, BUF_SIZE,
        IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_WRITE |
        IBV_ACCESS_REMOTE_READ);

    struct ibv_qp_init_attr qp_attr = {
        .send_cq = cq,
        .recv_cq = cq,
        .cap = {
            .max_send_wr = 32,
            .max_recv_wr = 32,
            .max_send_sge = 1,
            .max_recv_sge = 1,
        },
        .qp_type = IBV_QPT_RC,
    };
    rdma_create_qp(cm_id, pd, &qp_attr);

    /* Post receive before connecting */
    struct ibv_sge sge = {
        .addr = (uintptr_t)buf,
        .length = BUF_SIZE,
        .lkey = mr->lkey,
    };
    struct ibv_recv_wr recv_wr = { .sg_list = &sge, .num_sge = 1 };
    struct ibv_recv_wr *bad_wr;
    ibv_post_recv(cm_id->qp, &recv_wr, &bad_wr);

    /* Connect */
    struct rdma_conn_param conn_param = {
        .responder_resources = 16,
        .initiator_depth = 16,
        .retry_count = 7,
        .rnr_retry_count = 7,
    };
    rdma_connect(cm_id, &conn_param);

    rdma_get_cm_event(ec, &event);
    if (event->event != RDMA_CM_EVENT_ESTABLISHED) {
        fprintf(stderr, "Connection failed: %s\n",
                rdma_event_str(event->event));
        return 1;
    }
    rdma_ack_cm_event(event);
    printf("Connected!\n");

    /* --- Send data --- */
    snprintf(buf, BUF_SIZE, "Hello from RDMA client!");
    struct ibv_sge send_sge = {
        .addr = (uintptr_t)buf,
        .length = strlen(buf) + 1,
        .lkey = mr->lkey,
    };
    struct ibv_send_wr send_wr = {
        .sg_list = &send_sge,
        .num_sge = 1,
        .opcode = IBV_WR_SEND,
        .send_flags = IBV_SEND_SIGNALED,
    };
    struct ibv_send_wr *bad_send_wr;
    ibv_post_send(cm_id->qp, &send_wr, &bad_send_wr);

    /* Poll for completion */
    struct ibv_wc wc;
    while (ibv_poll_cq(cq, 1, &wc) == 0)
        ;
    if (wc.status != IBV_WC_SUCCESS) {
        fprintf(stderr, "Send failed: %s\n", ibv_wc_status_str(wc.status));
    }
    printf("Message sent\n");

    /* Disconnect */
    rdma_disconnect(cm_id);
    rdma_get_cm_event(ec, &event);
    rdma_ack_cm_event(event);

    /* Cleanup */
    rdma_destroy_qp(cm_id);
    ibv_dereg_mr(mr);
    ibv_destroy_cq(cq);
    ibv_dealloc_pd(pd);
    free(buf);
    rdma_destroy_id(cm_id);
    rdma_destroy_event_channel(ec);

    return 0;
}
```

---

## 11. Migration from Sockets to RDMA-CM

### 11.1 API Mapping

| Socket API | RDMA-CM API | Notes |
|------------|-------------|-------|
| socket() | rdma_create_id() | Use RDMA_PS_TCP for RC |
| bind() | rdma_bind_addr() | Same semantics |
| listen() | rdma_listen() | Same semantics |
| accept() | rdma_accept() | Event-driven model |
| connect() | rdma_resolve_addr() + rdma_resolve_route() + rdma_connect() | Multi-step |
| send()/write() | ibv_post_send() | Verbs API for data |
| recv()/read() | ibv_post_recv() + ibv_poll_cq() | Pre-posted buffers |
| close() | rdma_disconnect() + rdma_destroy_id() | Two-step |
| poll()/select() | rdma_get_cm_event() or poll(ec->fd) | Event-driven |

### 11.2 Key Differences

1. **Pre-posted receives**: Unlike sockets, RDMA requires receive buffers to be posted BEFORE data arrives. There is no kernel buffering.

2. **Memory registration**: All buffers used for RDMA must be registered. This is a significant difference from sockets where any buffer can be used.

3. **Zero-copy**: RDMA transfers data directly to/from registered buffers without kernel involvement. This eliminates copy overhead but requires careful buffer management.

4. **Event model**: RDMA-CM uses an explicit event model. Each operation (resolve, connect, etc.) generates an event that must be retrieved and acknowledged.

5. **No stream semantics**: RDMA Send/Receive operates on messages, not byte streams. Each send corresponds to exactly one receive completion. There is no partial delivery.

6. **Connection scope**: Each RDMA-CM connection creates a dedicated QP. For applications with thousands of connections, consider using Shared Receive Queues (SRQ) or XRC transport.

---

## 12. Helper Verbs (rdma_verbs.h)

The `rdma/rdma_verbs.h` header provides convenience wrappers that simplify common operations:

### 12.1 rdma_post_recv / rdma_post_send

```c
/* Simplified post receive */
int rdma_post_recv(struct rdma_cm_id *id, void *context,
                   void *addr, size_t length, struct ibv_mr *mr);

/* Simplified post send */
int rdma_post_send(struct rdma_cm_id *id, void *context,
                   void *addr, size_t length, struct ibv_mr *mr,
                   int flags);

/* Simplified RDMA write */
int rdma_post_write(struct rdma_cm_id *id, void *context,
                    void *addr, size_t length, struct ibv_mr *mr,
                    int flags, uint64_t remote_addr, uint32_t rkey);

/* Simplified RDMA read */
int rdma_post_read(struct rdma_cm_id *id, void *context,
                   void *addr, size_t length, struct ibv_mr *mr,
                   int flags, uint64_t remote_addr, uint32_t rkey);
```

```c
/* Example usage */
rdma_post_recv(cm_id, NULL, buf, BUF_SIZE, mr);
rdma_post_send(cm_id, NULL, buf, msg_len, mr, IBV_SEND_SIGNALED);
```

### 12.2 rdma_get_send_comp / rdma_get_recv_comp

```c
int rdma_get_send_comp(struct rdma_cm_id *id, struct ibv_wc *wc);
int rdma_get_recv_comp(struct rdma_cm_id *id, struct ibv_wc *wc);
```

Blocking calls that wait for a send or receive completion.

---

## 13. Advanced Topics

### 13.1 Private Data Exchange

RDMA-CM allows exchanging small amounts of data during connection setup:

```c
/* Client: send private data during connect */
struct my_conn_data {
    uint64_t buf_addr;
    uint32_t rkey;
    uint32_t buf_size;
};

struct my_conn_data client_data = {
    .buf_addr = (uint64_t)(uintptr_t)mr->addr,
    .rkey = mr->rkey,
    .buf_size = BUF_SIZE,
};

struct rdma_conn_param param = {
    .private_data = &client_data,
    .private_data_len = sizeof(client_data),
    .responder_resources = 16,
    .initiator_depth = 16,
};
rdma_connect(cm_id, &param);
```

```c
/* Server: receive private data in CONNECT_REQUEST event */
if (event->event == RDMA_CM_EVENT_CONNECT_REQUEST) {
    struct my_conn_data *peer_data =
        (struct my_conn_data *)event->param.conn.private_data;
    /* Copy before acking */
    uint64_t remote_addr = peer_data->buf_addr;
    uint32_t remote_rkey = peer_data->rkey;
}
```

**Private data size limits:**

| Transport | Max private_data_len (request) | Max private_data_len (reply) |
|-----------|-------------------------------|------------------------------|
| IB RC | 92 bytes | 196 bytes |
| iWARP | 512 bytes | 512 bytes |
| IB UD (SIDR) | 64 bytes | 136 bytes |

### 13.2 Non-blocking Event Processing with epoll

```c
struct rdma_event_channel *ec = rdma_create_event_channel();

/* Make channel non-blocking */
int flags = fcntl(ec->fd, F_GETFL);
fcntl(ec->fd, F_SETFL, flags | O_NONBLOCK);

/* Use with epoll */
int epfd = epoll_create1(0);
struct epoll_event ev = {
    .events = EPOLLIN,
    .data.ptr = ec,
};
epoll_ctl(epfd, EPOLL_CTL_ADD, ec->fd, &ev);

/* Event loop */
struct epoll_event events[10];
while (1) {
    int nfds = epoll_wait(epfd, events, 10, 1000);
    for (int i = 0; i < nfds; i++) {
        struct rdma_cm_event *cm_event;
        while (rdma_get_cm_event(ec, &cm_event) == 0) {
            /* Process event */
            rdma_ack_cm_event(cm_event);
        }
    }
}
```

### 13.3 Multicast with RDMA-CM

```c
/* Join a multicast group */
struct sockaddr_in6 mcast_addr;
/* Set up multicast address */

int ret = rdma_join_multicast(cm_id, (struct sockaddr *)&mcast_addr, NULL);
/* Wait for RDMA_CM_EVENT_MULTICAST_JOIN */

/* Leave multicast group */
rdma_leave_multicast(cm_id, (struct sockaddr *)&mcast_addr);
```

---

## 14. Error Handling

### 14.1 Common Errors and Solutions

| Error | Common Cause | Solution |
|-------|-------------|----------|
| ENODEV | No RDMA device for the address | Check ibv_devinfo, verify IP-to-device mapping |
| ETIMEDOUT | Address/route resolution timeout | Verify network connectivity, increase timeout |
| ECONNREFUSED | No server listening | Ensure server is running and listening |
| ECONNRESET | Connection reset by peer | Handle gracefully, reconnect if needed |
| ENOMEM | Resource allocation failure | Check ulimit, reduce resource count |
| ENETUNREACH | Network unreachable | Verify routing, check port state |

### 14.2 Debugging

```bash
# Enable RDMA-CM debug output
export RDMA_CM_DEBUG=1

# Check rdma-cm kernel module
lsmod | grep rdma_cm

# Verify RDMA device is associated with IP
rdma link show
ip addr show

# Monitor connection management events
rdma monitor
```

---

## 15. Thread Safety

RDMA-CM functions are thread-safe with the following considerations:

- Each `rdma_cm_id` should be used from a single thread at a time.
- Multiple threads can use different CM IDs on the same event channel.
- Event processing (`rdma_get_cm_event`) should be done from a single thread per channel.
- Creating multiple event channels allows true parallel event processing.
