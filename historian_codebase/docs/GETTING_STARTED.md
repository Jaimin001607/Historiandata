# Getting Started Guide

## Quick Start (5 minutes)

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Create Configuration File

```bash
python main.py --init-config
```

This creates a `config.yaml` file. Edit it with your historian database credentials:

```yaml
historian:
  type: custom_database
  connection_string: "your_database_connection_string"

components:
  PAFC_VALVE_01:
    metrics:
      vibration_rms:
        tag_name: "PAFC.VALVE_01.VIBRATION"
        unit: "mm/s"
        warning: 50
        critical: 75
```

### 3. Run the System

**Option A: Run with API Server** (recommended for production/dev)
```bash
python main.py --port 8000
```

Then access the API at: http://localhost:8000/docs

**Option B: Run Monitoring Only** (background monitoring without web server)
```bash
python main.py --monitor-only --interval 60
```

---

## Configuration

### Basic Configuration

Edit `config.yaml`:

```yaml
historian:
  type: custom_database
  connection_string: "your_connection_string"

monitoring:
  interval_seconds: 60              # Sample data every 60 seconds
  data_lookback_window: 300         # Analyze last 5 minutes of data
  enabled: true

components:
  COMPONENT_ID:
    description: "Human-readable description"
    type: "valve|pump|motor|etc"
    
    metrics:
      metric_name_1:
        tag_name: "HISTORIAN_TAG_NAME"
        unit: "units"
        warning: 50.0
        critical: 75.0
      
      metric_name_2:
        tag_name: "HISTORIAN_TAG_NAME"
        unit: "units"
        warning: 10.0
        critical: 20.0
```

### Common Configuration Scenarios

#### Scenario 1: Monitor 3 PAFC Valves
See `config.example.yaml` for complete PAFC setup.

#### Scenario 2: Add a New Valve
1. Create new component entry in `config.yaml`:
```yaml
components:
  PAFC_VALVE_04:
    metrics:
      vibration_rms:
        tag_name: "PAFC.VALVE_04.VIBRATION"
        unit: "mm/s"
        warning: 50
        critical: 75
```

2. Ensure the historian tag exists and contains data
3. Restart the system

#### Scenario 3: Adjust Thresholds
Based on historical baseline data:

```bash
# Establish baseline for 1 week of normal operation
# Example baseline range: 30-40 mm/s for vibration

# Set warning threshold: baseline_mean + 1.5σ = ~50 mm/s
# Set critical threshold: baseline_mean + 2.5σ = ~75 mm/s
```

---

## Testing

### Run Unit Tests

```bash
cd backend
pytest tests/ -v
```

### Run Specific Test

```bash
pytest tests/test_rms_calculator.py -v
```

### Test RMS Calculation

```python
from prognostics.metrics.rms_calculator import RMSCalculator

signal = [3, 4]
rms = RMSCalculator.calculate_rms(signal)
print(f"RMS: {rms:.2f}")  # Output: RMS: 3.54
```

### Test Threshold Engine

```python
from prognostics.thresholds.threshold_engine import ThresholdEngine

engine = ThresholdEngine()
alert = engine.evaluate_metric(
    component_id="VALVE_01",
    metric_name="vibration",
    current_value=60.0,
    threshold_warning=50.0,
    threshold_critical=75.0
)
print(f"Alert: {alert.message}")  # Prints warning alert
```

---

## API Usage

### Check System Health

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "monitor_running": true,
  "historian_connected": true,
  "timestamp": "2026-06-08T16:30:00Z"
}
```

### Get Active Alerts

```bash
curl http://localhost:8000/alerts
```

### Acknowledge Alert

```bash
curl -X POST http://localhost:8000/alerts/PAFC_VALVE_01/acknowledge
```

### List Components

```bash
curl http://localhost:8000/components
```

See `docs/API.md` for complete API reference.

---

## Troubleshooting

### Issue: "Cannot connect to historian"

**Solution**:
- Check `connection_string` in `config.yaml`
- Verify historian database is running
- Test connection manually:
```python
from prognostics.historian_connector import HistorianConnector
conn = HistorianConnector("your_connection_string")
print(conn.health_check())  # Should print True
```

### Issue: "No data for tag X"

**Solution**:
- Verify tag name matches historian database
- Check that tag has recent data in historian:
```python
from prognostics.historian_connector import HistorianConnector
from datetime import datetime, timedelta

conn = HistorianConnector("your_connection_string")
end = datetime.now()
start = end - timedelta(hours=1)
data = conn.get_tag_data("PAFC.VALVE_01.VIBRATION", start, end)
print(f"Data points: {len(data)}")
```

### Issue: "Thresholds generating too many false positives"

**Solution**:
- Review and adjust warning/critical thresholds
- Increase hysteresis window (default 10%):
```yaml
thresholds:
  default_hysteresis_percent: 20  # Increase from 10 to 20
```
- Run 1-2 weeks of baseline characterization before finalizing thresholds

### Issue: API returns 503 "Monitor not initialized"

**Solution**:
- Check logs: `tail -f prognostics.log`
- Ensure historian connection is working
- Restart the API server

---

## Development

### Project Structure

```
backend/
├── prognostics/
│   ├── __init__.py
│   ├── config.py              # Configuration loader
│   ├── historian_connector.py  # Database interface
│   ├── monitor.py             # Main monitoring engine
│   ├── api.py                 # FastAPI application
│   ├── metrics/
│   │   ├── rms_calculator.py   # RMS computation
│   │   └── health_engine.py    # Metric aggregation
│   └── thresholds/
│       └── threshold_engine.py # Alert generation
├── tests/
│   ├── test_rms_calculator.py
│   └── test_threshold_engine.py
├── main.py                    # Entry point
├── requirements.txt
└── config.example.yaml
```

### Adding a New Metric Type

1. Create calculator class in `prognostics/metrics/`:
```python
# prognostics/metrics/pressure_analyzer.py
class PressureAnalyzer:
    @staticmethod
    def calculate_pressure_variance(data):
        # Your logic here
        return variance
```

2. Update `HealthEngine` to use it:
```python
from .pressure_analyzer import PressureAnalyzer

# In calculate_health_metrics()
variance = PressureAnalyzer.calculate_pressure_variance(data)
```

3. Update configuration:
```yaml
metrics:
  pressure_variance:
    tag_name: "PAFC.VALVE_01.PRESSURE"
    unit: "psi"
    warning: 10
    critical: 20
```

### Running in Docker (Optional)

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY backend/ .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t prognostics .
docker run -p 8000:8000 -v $(pwd)/config.yaml:/app/config.yaml prognostics
```

---

## Next Steps

1. **Configure Historian Connection**
   - Update `config.yaml` with your database credentials
   - Test connection with health check

2. **Identify Component Tags**
   - Reference `docs/TAG_CATALOG.md`
   - Add all monitored components to config

3. **Establish Baselines**
   - Run 1-2 weeks of monitoring in normal operation
   - Document normal value ranges

4. **Set Thresholds**
   - Use baseline statistics to set warning/critical levels
   - Document threshold rationale

5. **Test Alerting**
   - Simulate threshold violations with synthetic data
   - Validate frontend notifications
   - Train operators on alert response

6. **Deploy to Production**
   - Run in Docker or systemd service
   - Set up monitoring/logging aggregation
   - Configure backup/failover

---

## Support

- **API Documentation**: See `docs/API.md`
- **Tag Reference**: See `docs/TAG_CATALOG.md`
- **Technical Details**: See `docs/MEMO.md`
- **Code Comments**: See inline docstrings in Python modules

For questions or issues, contact the Equipment Monitoring Team.

---

**Last Updated**: 2026-06-08
