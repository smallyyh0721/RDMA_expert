"""CLI entry point for RDMA Network Monitor.

Usage:
    python -m rdma_monitor [--config /path/to/config.yaml]
"""

import argparse
import sys

from rdma_monitor.monitor import RDMAMonitor


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RDMA Network Monitor - monitor IB/RoCE performance, "
                    "topology, congestion and link status"
    )
    parser.add_argument(
        "-c", "--config",
        default=None,
        help="Path to YAML configuration file "
             "(default: auto-detect from standard locations)",
    )
    args = parser.parse_args()

    monitor = RDMAMonitor(config_path=args.config)
    try:
        monitor.start()
    except KeyboardInterrupt:
        monitor.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
