FROM python:3.12-slim

# Install RDMA userspace tools (available in Debian/Ubuntu repos)
RUN apt-get update && apt-get install -y --no-install-recommends \
    rdma-core \
    ibverbs-utils \
    infiniband-diags \
    ethtool \
    iproute2 \
    perftest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/rdma_monitor

# Prometheus metrics port
EXPOSE 9090

ENTRYPOINT ["python", "-m", "rdma_monitor"]
CMD ["--config", "/app/rdma_monitor/config.yaml"]
