# Linux Log Monitor with Prometheus Metrics

A production-grade Python tool that monitors Linux system log files in real time, detects critical events using configurable keyword matching, exposes metrics for Prometheus scraping, and sends instant Slack alerts — designed for high-availability DevOps environments.

---

## Why I Built This

While working on the Verizon ENM Deployment Platform at Ericsson, I needed a lightweight, customizable log monitoring solution that could:

- Watch multiple log files simultaneously without missing entries during log rotation
- Expose metrics natively to our existing Prometheus + Grafana stack
- Send instant Slack notifications for critical production events
- Run as a systemd service with zero manual intervention

Existing tools were either too heavy (Logstash) or required complex setup (Filebeat + ELK). This tool runs with a single Python file and a JSON config.

---

## Features

- **Real-time log tailing** — watches multiple log files simultaneously
- **Log rotation handling** — automatically resets file position on rotation
- **Configurable keyword matching** — define your own CRITICAL / ERROR / WARNING patterns via JSON
- **Prometheus metrics** — exposes counters and gauges for Grafana dashboards
- **Slack alerting** — instant webhook notifications for CRITICAL and ERROR events
- **Systemd ready** — runs as a background service on any Linux server

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.8+ |
| Metrics | Prometheus client |
| Alerting | Slack Webhooks |
| OS | Linux (Ubuntu / RHEL / CentOS) |
| Monitoring | Prometheus + Grafana |
| Process management | systemd |

---

## Project Structure

```
linux-log-monitor/
├── log_monitor.py          # Main monitoring script
├── requirements.txt        # Python dependencies
├── config/
│   └── config.json         # Log files, keywords, Slack webhook config
├── alerts/
│   └── alert_rules.yml     # Prometheus alerting rules
└── README.md
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/linux-log-monitor.git
cd linux-log-monitor
```

### 2. Install dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Configure

Edit `config/config.json` to set your log file paths, keywords, and Slack webhook URL:

```json
{
  "scan_interval_seconds": 30,
  "slack_webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
  "log_files": [
    "/var/log/syslog",
    "/var/log/auth.log",
    "/var/log/nginx/error.log"
  ],
  "keywords": {
    "CRITICAL": ["CRITICAL", "FATAL", "KERNEL PANIC", "OUT OF MEMORY"],
    "ERROR":    ["ERROR", "EXCEPTION", "CONNECTION REFUSED", "TIMEOUT"],
    "WARNING":  ["WARNING", "DEPRECATED", "RETRY"]
  }
}
```

### 4. Run

```bash
python3 log_monitor.py --config config/config.json --metrics-port 8000
```

### 5. Verify Prometheus metrics

Open your browser or curl the metrics endpoint:

```bash
curl http://localhost:8000/metrics
```

You should see output like:

```
# HELP log_monitor_errors_total Total error lines detected
# TYPE log_monitor_errors_total counter
log_monitor_errors_total{log_file="/var/log/syslog"} 3.0

# HELP log_monitor_critical_total Total critical lines detected
# TYPE log_monitor_critical_total counter
log_monitor_critical_total{log_file="/var/log/auth.log"} 1.0
```

---

## Running as a systemd Service

Create `/etc/systemd/system/log-monitor.service`:

```ini
[Unit]
Description=Linux Log Monitor
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/linux-log-monitor
ExecStart=/usr/bin/python3 /opt/linux-log-monitor/log_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable log-monitor
sudo systemctl start log-monitor
sudo systemctl status log-monitor
```

---

## Prometheus Configuration

Add this job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'log_monitor'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 30s
```

Then load the alert rules from `alerts/alert_rules.yml` in your Prometheus configuration:

```yaml
rule_files:
  - "alerts/alert_rules.yml"
```

---

## Grafana Dashboard

After connecting Prometheus as a data source, use these queries to build your dashboard:

| Panel | Query |
|---|---|
| Total errors (last 1h) | `increase(log_monitor_errors_total[1h])` |
| Critical events rate | `rate(log_monitor_critical_total[5m])` |
| Lines scanned/sec | `rate(log_monitor_lines_scanned_total[1m])` |
| Last scan time | `time() - log_monitor_last_scan_timestamp` |

---

## Alerting Rules

The `alerts/alert_rules.yml` file includes three pre-built Prometheus alerts:

| Alert | Condition | Severity |
|---|---|---|
| CriticalLogDetected | Any CRITICAL keyword detected in 5m | Critical |
| HighErrorRate | Error rate > 0.5/sec for 2 minutes | Warning |
| LogMonitorDown | No scan completed in 2 minutes | Critical |

---

## Environment Variables (Optional)

You can override config values using environment variables:

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export SCAN_INTERVAL=60
export METRICS_PORT=9090
```

---

## Real-World Usage

This tool was built based on patterns used in enterprise telecom infrastructure monitoring. It handles:

- High-volume log files (1M+ lines/day)
- Multi-environment deployments (dev / staging / production)
- Integration with existing Prometheus + Grafana observability stacks
- Zero-downtime log rotation on production Linux servers

---

## Author

**Ajay Mahaveer Patil**
Cloud & DevOps Engineer | CKA Certified | 4+ Years at Ericsson

- LinkedIn: [linkedin.com/in/ajaypatil9](https://www.linkedin.com/in/ajaypatil9/)
- CKA Badge: [Credly](https://www.credly.com/badges/e5aeadd3-ac52-46f5-bf05-4a8178d50c5a/public_url)

---

## License

MIT License — free to use and modify.
