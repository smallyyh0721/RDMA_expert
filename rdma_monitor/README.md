# RDMA Network Monitor

A flexible, scalable Python monitor for **InfiniBand** and **RoCE** RDMA networks.
Auto-detects network type, collects metrics, exports to Prometheus, saves JSON snapshots, and integrates with LLM / Dify AI for automated analysis.

## Features

| Feature | Description |
|---------|-------------|
| **Auto-detection** | Detects IB vs RoCE from sysfs / ibstat and applies the right collectors |
| **Performance** | Port counters, throughput rates, perfquery (IB), ethtool stats (RoCE) |
| **Topology** | GID/LID tables, ibnetdiscover, switch/HCA enumeration |
| **Configuration** | Firmware info, mlxconfig, kernel module params, ethtool offloads |
| **Congestion** | ECN/CNP counters, PFC stats, buffer overruns, DCQCN settings |
| **Link Status** | Physical state, cable info, symbol errors, link-flap detection |
| **Prometheus** | All metrics exported as Prometheus gauges on a configurable port |
| **JSON Snapshots** | Periodic full-state dumps (default every 30 s) |
| **LLM Analysis** | Sends snapshots to any OpenAI-compatible API for expert analysis |
| **Dify AI** | Pushes data to Dify workflows for custom AI automation |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with default config
sudo python -m rdma_monitor

# Run with custom config
sudo python -m rdma_monitor --config /path/to/config.yaml
```

> **Note:** Most RDMA counters require root or `CAP_NET_ADMIN`.

## Configuration

Edit `config.yaml` to customise behaviour. Key sections:

```yaml
general:
  poll_interval: 10      # seconds between collection cycles
  snapshot_interval: 30  # seconds between JSON dumps
  snapshot_dir: ./snapshots

network:
  mode: auto             # auto | ib | roce
  devices: []            # empty = all devices

prometheus:
  enabled: true
  port: 9090

llm:
  enabled: false
  api_url: "https://api.openai.com/v1/chat/completions"
  api_key: ""            # set via env RDMA_MON_LLM__API_KEY
  model: gpt-4

dify:
  enabled: false
  api_url: "http://localhost/v1"
  api_key: ""
  workflow_id: ""
```

Every setting can be overridden with environment variables using the
pattern `RDMA_MON_<SECTION>__<KEY>`. For example:

```bash
export RDMA_MON_LLM__API_KEY="sk-..."
export RDMA_MON_PROMETHEUS__PORT=9100
```

## Docker

```bash
docker build -t rdma-monitor -f Dockerfile .
docker run --privileged --network=host \
  -v /sys:/sys:ro \
  -e RDMA_MON_LLM__API_KEY="sk-..." \
  rdma-monitor
```

## Architecture

```
rdma_monitor/
├── __main__.py              # CLI entry point
├── monitor.py               # Main orchestrator / event loop
├── config.yaml              # Default configuration
├── collectors/
│   ├── base.py              # Abstract BaseCollector
│   ├── performance.py       # Throughput, counters, rates
│   ├── topology.py          # GIDs, LIDs, fabric discovery
│   ├── configuration.py     # FW, mlxconfig, kernel params
│   ├── congestion.py        # ECN, PFC, CNP, buffer stats
│   └── link_status.py       # Link state, cable, flap detection
├── exporters/
│   ├── prometheus_exporter.py
│   └── json_exporter.py
├── analysis/
│   ├── llm_analyzer.py      # OpenAI-compatible LLM integration
│   └── dify_client.py       # Dify AI workflow client
└── utils/
    ├── config_loader.py     # YAML + env-var config loading
    └── network_detector.py  # IB/RoCE auto-detection
```

## Extending

To add a new collector:

1. Create a new file in `collectors/`
2. Subclass `BaseCollector` and implement `collect() -> dict`
3. Register it in `monitor.py` `_init_collectors()`

The `collect()` return dict is automatically flattened into Prometheus
gauges and included in JSON snapshots.
