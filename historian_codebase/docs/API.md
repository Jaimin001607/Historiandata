# RMS Prognostics API Documentation

Base URL: `http://localhost:8000`

---

## Health Check Endpoints

### System Health Check
```
GET /health
```

**Description**: Check if the monitoring system is operational.

**Response**:
```json
{
  "status": "healthy",
  "monitor_running": true,
  "historian_connected": true,
  "timestamp": "2026-06-08T16:30:00.000Z"
}
```

**Status Values**:
- `healthy` - All systems operational
- `degraded` - System running but with issues (e.g., historian connection unstable)
- `offline` - System not operational

---

## Component Endpoints

### List All Components
```
GET /components
```

**Description**: Get list of all monitored components.

**Response**:
```json
{
  "components": ["PAFC_VALVE_01", "PAFC_VALVE_02", "PAFC_VALVE_03"],
  "total": 3,
  "timestamp": "2026-06-08T16:30:00.000Z"
}
```

### Get Component Health
```
GET /component/{component_id}/health
```

**Description**: Get current health status for a specific component.

**Parameters**:
- `component_id` (path): Component identifier (e.g., `PAFC_VALVE_01`)

**Response**:
```json
{
  "component_id": "PAFC_VALVE_01",
  "overall_status": "warning",
  "metrics": {
    "vibration_rms": {
      "metric_name": "vibration_rms",
      "value": 55.2,
      "unit": "mm/s",
      "status": "warning",
      "threshold_warning": 50.0,
      "threshold_critical": 75.0
    },
    "pressure_variance": {
      "metric_name": "pressure_variance",
      "value": 8.5,
      "unit": "psi",
      "status": "healthy",
      "threshold_warning": 10.0,
      "threshold_critical": 20.0
    }
  },
  "timestamp": "2026-06-08T16:30:00.000Z",
  "alert_triggered": true,
  "alert_message": "PAFC_VALVE_01: High vibration RMS (55.2 mm/s, +10.4%)"
}
```

**Status Values**:
- `healthy` - All metrics nominal
- `warning` - At least one metric exceeds warning threshold
- `critical` - At least one metric exceeds critical threshold

---

## Alert Endpoints

### Get Active Alerts
```
GET /alerts
```

**Description**: Get all currently active alerts.

**Response**:
```json
{
  "alerts": [
    {
      "component_id": "PAFC_VALVE_01",
      "level": "warning",
      "metric": "vibration_rms",
      "value": 55.2,
      "threshold": 50.0,
      "message": "[WARNING] PAFC_VALVE_01 - vibration_rms at 55.2 (threshold: 50.0, +10.4%)",
      "timestamp": "2026-06-08T16:30:00.000Z",
      "acknowledged": false
    }
  ],
  "total": 1,
  "timestamp": "2026-06-08T16:30:00.000Z"
}
```

**Alert Levels**:
- `info` - Informational, no action required
- `warning` - Precursor to failure, maintenance recommended
- `critical` - Immediate failure risk, action required

### Get Alert History
```
GET /alerts/history
```

**Description**: Get historical alerts.

**Query Parameters**:
- `limit` (optional): Maximum number of alerts to return (default: 100)

**Response**:
```json
{
  "alerts": [
    {
      "component_id": "PAFC_VALVE_01",
      "level": "critical",
      "metric": "vibration_rms",
      "value": 78.5,
      "threshold": 75.0,
      "message": "[CRITICAL] PAFC_VALVE_01 - vibration_rms at 78.5 (threshold: 75.0, +4.7%)",
      "timestamp": "2026-06-08T16:15:00.000Z",
      "acknowledged": true
    },
    {
      "component_id": "PAFC_VALVE_02",
      "level": "warning",
      "metric": "temperature_trend",
      "value": 65.0,
      "threshold": 70.0,
      "message": "[WARNING] PAFC_VALVE_02 - temperature_trend at 65.0 (threshold: 70.0, -7.1%)",
      "timestamp": "2026-06-08T16:00:00.000Z",
      "acknowledged": false
    }
  ],
  "total": 2,
  "timestamp": "2026-06-08T16:30:00.000Z"
}
```

### Acknowledge Alert
```
POST /alerts/{component_id}/acknowledge
```

**Description**: Mark an alert as acknowledged by the user.

**Parameters**:
- `component_id` (path): Component identifier

**Request Body**: (none)

**Response**:
```json
{
  "component_id": "PAFC_VALVE_01",
  "acknowledged": true,
  "timestamp": "2026-06-08T16:30:00.000Z"
}
```

**Notes**:
- Acknowledging an alert doesn't clear it; alert remains until metric improves
- Used for tracking which alerts have been reviewed by operators

---

## Monitoring Control Endpoints

### Start Monitor
```
POST /monitor/start
```

**Description**: Start the monitoring system.

**Response**:
```json
{
  "status": "started",
  "timestamp": "2026-06-08T16:30:00.000Z"
}
```

### Stop Monitor
```
POST /monitor/stop
```

**Description**: Stop the monitoring system (no new metrics will be calculated).

**Response**:
```json
{
  "status": "stopped",
  "timestamp": "2026-06-08T16:30:00.000Z"
}
```

### Get Monitor Status
```
GET /monitor/status
```

**Description**: Get current monitoring system status.

**Response**:
```json
{
  "running": true,
  "interval_seconds": 60,
  "active_components": 3,
  "active_alerts": 1,
  "timestamp": "2026-06-08T16:30:00.000Z"
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad request (invalid parameters) |
| 404 | Resource not found (component doesn't exist) |
| 503 | Service unavailable (historian disconnected) |
| 500 | Internal server error |

**Example Error**:
```json
{
  "detail": "Component PAFC_VALVE_99 not found"
}
```

---

## Webhook Integration (Future)

The system can be extended to send alerts to external webhooks:

```python
POST http://your-webhook-url.com/alerts
Content-Type: application/json

{
  "component_id": "PAFC_VALVE_01",
  "level": "critical",
  "metric": "vibration_rms",
  "value": 78.5,
  "threshold": 75.0,
  "message": "...",
  "timestamp": "2026-06-08T16:30:00.000Z"
}
```

---

## Rate Limiting

- No rate limiting currently implemented (TODO)
- Recommended: 100 requests/minute per client

---

## Authentication

- Currently unauthenticated (TODO)
- Future: API key or JWT token-based auth

---

## API Version

Current version: **1.0.0**

Supported from: 2026-06-08 onwards

---

**Last Updated**: 2026-06-08
