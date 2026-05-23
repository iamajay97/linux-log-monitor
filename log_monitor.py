#!/usr/bin/env python3
"""
log_monitor.py
--------------
Monitors Linux system log files for critical keywords,
sends alerts to a Slack webhook, and exposes metrics
for Prometheus scraping.

Author : Ajay Mahaveer Patil
Stack  : Python 3 | Prometheus client | Linux
"""

import os
import re
import time
import json
import logging
import argparse
import requests
from datetime import datetime
from prometheus_client import start_http_server, Counter, Gauge

# ── Logging setup ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("log_monitor")

# ── Prometheus metrics ─────────────────────────────────────────
ERRORS_TOTAL     = Counter("log_monitor_errors_total",
                           "Total error lines detected", ["log_file"])
WARNINGS_TOTAL   = Counter("log_monitor_warnings_total",
                           "Total warning lines detected", ["log_file"])
CRITICAL_TOTAL   = Counter("log_monitor_critical_total",
                           "Total critical lines detected", ["log_file"])
LAST_SCAN_TIME   = Gauge("log_monitor_last_scan_timestamp",
                         "Unix timestamp of last successful scan")
LINES_SCANNED    = Counter("log_monitor_lines_scanned_total",
                           "Total log lines scanned", ["log_file"])


# ── Config loader ──────────────────────────────────────────────
def load_config(config_path: str) -> dict:
    with open(config_path, "r") as f:
        return json.load(f)


# ── Slack alerting ─────────────────────────────────────────────
def send_slack_alert(webhook_url: str, message: str, severity: str):
    colour_map = {"CRITICAL": "#FF0000", "ERROR": "#FF8C00", "WARNING": "#FFD700"}
    payload = {
        "attachments": [{
            "color"  : colour_map.get(severity, "#36a64f"),
            "title"  : f"[{severity}] Log Monitor Alert",
            "text"   : message,
            "footer" : "linux-log-monitor",
            "ts"     : int(time.time()),
        }]
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=5)
        resp.raise_for_status()
        logger.info("Slack alert sent: %s", severity)
    except requests.RequestException as exc:
        logger.error("Failed to send Slack alert: %s", exc)


# ── Core monitor ───────────────────────────────────────────────
class LogMonitor:
    def __init__(self, config: dict):
        self.config       = config
        self.log_files    = config.get("log_files", [])
        self.keywords     = config.get("keywords", {})
        self.slack_url    = config.get("slack_webhook_url", "")
        self.scan_interval = config.get("scan_interval_seconds", 30)
        self._file_pos    = {}          # track read position per file

    def _tail_file(self, path: str):
        """Yield new lines added to a file since last read."""
        if not os.path.exists(path):
            logger.warning("Log file not found: %s", path)
            return

        current_size = os.path.getsize(path)
        last_pos = self._file_pos.get(path, current_size)  # start from EOF on first run

        # Handle log rotation
        if current_size < last_pos:
            logger.info("Log rotation detected for %s — resetting position.", path)
            last_pos = 0

        if current_size == last_pos:
            return

        with open(path, "r", errors="replace") as fh:
            fh.seek(last_pos)
            for line in fh:
                yield line
            self._file_pos[path] = fh.tell()

    def _classify_line(self, line: str):
        """Return severity if line matches a keyword, else None."""
        line_upper = line.upper()
        for severity, patterns in self.keywords.items():
            for pattern in patterns:
                if re.search(pattern, line_upper):
                    return severity.upper()
        return None

    def scan(self):
        """One scan pass across all configured log files."""
        for log_path in self.log_files:
            for line in self._tail_file(log_path):
                line = line.strip()
                if not line:
                    continue

                LINES_SCANNED.labels(log_file=log_path).inc()
                severity = self._classify_line(line)

                if severity == "CRITICAL":
                    CRITICAL_TOTAL.labels(log_file=log_path).inc()
                    logger.critical("[%s] %s", log_path, line)
                    if self.slack_url:
                        send_slack_alert(self.slack_url,
                                         f"*File*: `{log_path}`\n```{line}```",
                                         "CRITICAL")

                elif severity == "ERROR":
                    ERRORS_TOTAL.labels(log_file=log_path).inc()
                    logger.error("[%s] %s", log_path, line)
                    if self.slack_url:
                        send_slack_alert(self.slack_url,
                                         f"*File*: `{log_path}`\n```{line}```",
                                         "ERROR")

                elif severity == "WARNING":
                    WARNINGS_TOTAL.labels(log_file=log_path).inc()
                    logger.warning("[%s] %s", log_path, line)

        LAST_SCAN_TIME.set(time.time())

    def run(self):
        logger.info("Log monitor started. Scan interval: %ss", self.scan_interval)
        while True:
            try:
                self.scan()
            except Exception as exc:
                logger.exception("Unexpected error during scan: %s", exc)
            time.sleep(self.scan_interval)


# ── Entry point ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Linux Log Monitor with Prometheus metrics")
    parser.add_argument("--config",   default="config/config.json",
                        help="Path to JSON config file")
    parser.add_argument("--metrics-port", type=int, default=8000,
                        help="Port to expose Prometheus metrics (default: 8000)")
    args = parser.parse_args()

    config = load_config(args.config)

    logger.info("Starting Prometheus metrics server on port %d", args.metrics_port)
    start_http_server(args.metrics_port)

    monitor = LogMonitor(config)
    monitor.run()


if __name__ == "__main__":
    main()
