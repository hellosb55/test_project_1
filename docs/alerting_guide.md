# Alerting System Guide

## Overview

The alerting system adds threshold-based monitoring to the metrics collection agent. When metric values exceed configured thresholds for a specified duration, notifications are sent through email, Slack, or custom webhooks.

## Features

- **Threshold-based alerts**: Define rules with operators (>, <, >=, <=, ==, !=) and thresholds
- **Duration tracking**: Only trigger after condition persists for specified minutes
- **Cooldown periods**: Prevent alert spam with configurable cooldown between notifications
- **Multiple channels**: Email (SMTP), Slack (Webhook), Custom HTTP webhooks
- **Alert history**: SQLite storage with configurable retention
- **Label filtering**: Target specific metric instances (e.g., specific disk mount points)
- **Severity levels**: info, warning, critical

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Agent Process                         │
├─────────────────────────────────────────────────────────────┤
│  Collector Threads       │  Alert Evaluator Thread          │
│  - CPU Collector         │  - Read metrics from registry    │
│  - Memory Collector      │  - Evaluate rules                │
│  - Disk Collector        │  - Track alert states            │
│  - Network Collector     │  - Send notifications            │
│  - Process Collector     │                                  │
├──────────────────────────┴──────────────────────────────────┤
│           Prometheus Registry (Shared)                       │
└─────────────────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
  /metrics endpoint          Notification Channels
                            (Email, Slack, Webhook)
```

### Components

1. **AlertRule**: Rule definition with metric, condition, and notification settings
2. **AlertEvaluator**: Evaluates rules every N seconds against current metrics
3. **AlertManager**: Tracks alert state (triggered → active → resolved)
4. **Storage**: SQLite backend for alert history
5. **Channels**: Notification delivery (Email, Slack, Webhook)

## Configuration

### Enable Alerting

Edit `config/agent.yaml`:

```yaml
alerting:
  enabled: true
  evaluation_interval: 30  # Check rules every 30 seconds
  alert_rules_file: "config/alerts.yaml"

  channels:
    email:
      enabled: true
      smtp_host: "smtp.gmail.com"
      smtp_port: 587
      smtp_user: "alerts@example.com"
      smtp_password: "${EMAIL_PASSWORD}"
      from_address: "alerts@example.com"
      to_addresses:
        - "admin@example.com"

    slack:
      enabled: true
      webhook_url: "${SLACK_WEBHOOK_URL}"
      channel: "#alerts"
```

### Define Alert Rules

Create `config/alerts.yaml`:

```yaml
alert_rules:
  - name: "high_cpu_usage"
    description: "CPU usage exceeds 80% for 5 minutes"
    metric_name: "cpu_usage_percent"
    condition:
      operator: ">"
      threshold: 80.0
    for_duration_minutes: 5
    severity: "warning"
    channels:
      - email
      - slack
    cooldown_minutes: 15
    enabled: true
```

### Rule Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique rule identifier |
| `metric_name` | string | Yes | Prometheus metric name to monitor |
| `condition.operator` | string | Yes | Comparison operator: >, <, >=, <=, ==, != |
| `condition.threshold` | float | Yes | Threshold value |
| `for_duration_minutes` | int | Yes | How long condition must persist |
| `severity` | string | Yes | info, warning, or critical |
| `channels` | list | Yes | Notification channels: email, slack, webhook |
| `cooldown_minutes` | int | No | Minimum time between notifications (default: 15) |
| `label_selector` | dict | No | Filter by specific label values |
| `annotations` | dict | No | Custom summary and description templates |
| `labels` | dict | No | Metadata labels for the alert |
| `enabled` | bool | No | Enable/disable rule (default: true) |

### Label Selectors

Filter metrics by labels:

```yaml
- name: "root_disk_full"
  metric_name: "disk_usage_percent"
  label_selector:
    mount_point: "/"  # Only alert for root filesystem
  condition:
    operator: ">"
    threshold: 90.0
  for_duration_minutes: 10
  severity: "critical"
  channels: [email]
```

### Template Variables

Use in `annotations.summary` and `annotations.description`:

- `{{ value }}` - Current metric value
- `{{ threshold }}` - Alert threshold
- `{{ labels.key }}` - Label values

Example:

```yaml
annotations:
  summary: "High CPU on {{ labels.hostname }}"
  description: "CPU usage is {{ value }}% (threshold: {{ threshold }}%)"
```

## Usage

### Start Agent with Alerting

```bash
# Set environment variables for sensitive credentials
export EMAIL_PASSWORD="your_smtp_password"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Start agent
python run_agent.py --config config/agent.yaml
```

### View Alert History

Query SQLite database:

```bash
sqlite3 ./data/alerts.db

# View recent alerts
SELECT alert_id, rule_name, state, severity, metric_value, triggered_at
FROM alert_history
ORDER BY triggered_at DESC
LIMIT 10;

# Count alerts by severity
SELECT severity, COUNT(*)
FROM alert_history
WHERE state = 'active'
GROUP BY severity;

# View notification history
SELECT alert_id, notification_count, last_notified_at
FROM alert_history
WHERE notification_count > 0;
```

## Notification Channels

### Email (SMTP)

**Gmail Example:**

1. Enable 2-factor authentication in Google Account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Configure:

```yaml
email:
  enabled: true
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  smtp_user: "your-email@gmail.com"
  smtp_password: "${EMAIL_PASSWORD}"
  use_tls: true
  from_address: "your-email@gmail.com"
  to_addresses:
    - "admin@example.com"
```

### Slack Webhook

1. Create Incoming Webhook: https://api.slack.com/messaging/webhooks
2. Configure:

```yaml
slack:
  enabled: true
  webhook_url: "${SLACK_WEBHOOK_URL}"
  channel: "#alerts"
  username: "Metrics Agent"
```

### Custom Webhook

POST JSON to any HTTP endpoint:

```yaml
webhook:
  enabled: true
  url: "https://your-service.example.com/alerts"
  method: "POST"
  headers:
    Authorization: "Bearer ${API_TOKEN}"
  timeout: 10
```

**Payload format:**

```json
{
  "alert": {
    "name": "high_cpu_usage",
    "severity": "warning",
    "status": "firing",
    "timestamp": "2026-02-02T12:34:56"
  },
  "metric": {
    "name": "cpu_usage_percent",
    "value": 85.2,
    "threshold": 80.0,
    "operator": ">"
  },
  "labels": {"host": "server1"},
  "annotations": {
    "summary": "High CPU usage detected",
    "description": "CPU usage is 85.2% (threshold: 80%)"
  }
}
```

## Alert Lifecycle

1. **Triggered**: Condition met, start tracking duration
2. **Active**: Duration requirement met, notifications sent
3. **Resolved**: Condition no longer met, alert cleared

```
Metric value exceeds threshold
  │
  ▼
TRIGGERED (waiting for duration)
  │ for_duration_minutes elapsed
  ▼
ACTIVE (send notification)
  │ cooldown_minutes elapsed
  ▼
ACTIVE (can notify again)
  │ condition no longer met
  ▼
RESOLVED (cleanup)
```

## Best Practices

### 1. Tune Thresholds and Durations

Avoid alert fatigue:

```yaml
# Too sensitive (alerts every spike)
for_duration_minutes: 1

# Better (alerts sustained issues)
for_duration_minutes: 5
```

### 2. Use Appropriate Cooldowns

```yaml
# Warning alerts: longer cooldown
severity: "warning"
cooldown_minutes: 15

# Critical alerts: shorter cooldown
severity: "critical"
cooldown_minutes: 5
```

### 3. Layer Severity Levels

```yaml
# Warning at 80%
- name: "high_cpu_usage"
  threshold: 80.0
  severity: "warning"

# Critical at 95%
- name: "critical_cpu_usage"
  threshold: 95.0
  severity: "critical"
```

### 4. Monitor Collector Health

```yaml
- name: "collector_unhealthy"
  metric_name: "agent_collector_status"
  condition:
    operator: "=="
    threshold: 0  # 0 = unhealthy
  for_duration_minutes: 1
  severity: "critical"
  channels: [slack]
```

### 5. Secure Credentials

Never commit credentials to version control:

```bash
# Use environment variables
export EMAIL_PASSWORD="..."
export SLACK_WEBHOOK_URL="..."

# Or use secrets management (HashiCorp Vault, AWS Secrets Manager)
```

## Troubleshooting

### Alerts Not Triggering

1. **Check rule is enabled:**
   ```yaml
   enabled: true
   ```

2. **Verify metric name:**
   ```bash
   curl http://localhost:9100/metrics | grep your_metric_name
   ```

3. **Check evaluation logs:**
   ```bash
   # Set log level to DEBUG
   export LOG_LEVEL=DEBUG
   python run_agent.py
   ```

4. **Verify duration requirement:**
   - Condition must persist for `for_duration_minutes`
   - Check metric is consistently above/below threshold

### Notifications Not Sending

1. **Verify channel is enabled:**
   ```yaml
   channels:
     email:
       enabled: true  # Must be true
   ```

2. **Check credentials:**
   ```bash
   # Test SMTP manually
   python -c "
   import smtplib
   with smtplib.SMTP('smtp.gmail.com', 587) as s:
       s.starttls()
       s.login('user', 'password')
   "
   ```

3. **Check cooldown period:**
   - Notifications limited by `cooldown_minutes`
   - Check `last_notified_at` in database

4. **Review logs:**
   ```bash
   grep "Failed to send" logs/agent.log
   ```

### High Memory Usage

If alert storage grows too large:

1. **Reduce retention:**
   ```yaml
   storage:
     retention_days: 7  # Keep less history
   ```

2. **Manual cleanup:**
   ```bash
   sqlite3 ./data/alerts.db "DELETE FROM alert_history WHERE triggered_at < date('now', '-7 days');"
   ```

## Performance Impact

Expected overhead with alerting enabled:

- **CPU**: +0.2-0.3% (30s evaluation, 50 rules)
- **Memory**: +10-15 MB (alert state cache + SQLite)
- **Disk**: ~10-50 MB (30 days history, 1000 alerts/day)

Well within agent resource limits (2% CPU, 50 MB memory).

## Examples

### Basic CPU Alert

```yaml
- name: "high_cpu"
  metric_name: "cpu_usage_percent"
  condition:
    operator: ">"
    threshold: 80.0
  for_duration_minutes: 5
  severity: "warning"
  channels: [email]
  cooldown_minutes: 15
  enabled: true
```

### Disk Space Alert with Labels

```yaml
- name: "disk_full"
  metric_name: "disk_usage_percent"
  label_selector:
    mount_point: "/"
  condition:
    operator: ">"
    threshold: 90.0
  for_duration_minutes: 10
  severity: "critical"
  annotations:
    summary: "Disk {{ labels.mount_point }} almost full"
    description: "Usage: {{ value }}% (threshold: {{ threshold }}%)"
  channels: [email, slack]
  enabled: true
```

### Network Error Alert

```yaml
- name: "network_errors"
  metric_name: "network_errors_total"
  condition:
    operator: ">"
    threshold: 100
  for_duration_minutes: 5
  severity: "warning"
  annotations:
    summary: "High network errors on {{ labels.interface }}"
  channels: [slack]
  enabled: true
```

## Next Steps

- **Week 6**: Add REST API for alert management (create/update/delete rules via HTTP)
- **Week 7**: Build web dashboard for viewing alerts and managing rules
- **Phase 3**: Integrate with Grafana for visualization

## References

- Main documentation: `docs/README.md`
- Configuration: `config/agent.example.yaml`, `config/alerts.example.yaml`
- Alert rules: `src/alerts/alert_rule.py`
- Storage: `src/alerts/storage/sqlite_storage.py`
- Channels: `src/alerts/channels/`
