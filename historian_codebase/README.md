# RMS-Based Equipment Prognostics System

A real-time health monitoring engine for equipment components using Root Mean Square (RMS) analysis of sensor data.

## Overview

This system monitors equipment (valves, motors, pumps) by:
1. **Sampling** sensor data from a custom Historian database (1-min intervals)
2. **Processing** RMS-based health metrics from raw signals
3. **Comparing** metrics against configurable thresholds
4. **Alerting** via frontend notifications when degradation is detected

## Project Status

- **Phase 1**: Setup & Analysis (In Progress)
- **Phase 2**: Core Engine Development (Pending)
- **Phase 3**: PAFC Trial Implementation (Pending)
- **Phase 4**: Frontend Integration (Pending)
- **Phase 5**: Documentation & Delivery (Pending)

## Quick Start

```bash
# Backend setup (Python)
cd backend
pip install -r requirements.txt

# Configure historian connection
cp config.example.yaml config.yaml
# Edit config.yaml with your historian details

# Run monitoring engine
python -m prognostics.monitor
```

## Project Structure

```
.
├── backend/                          # Python backend
│   ├── prognostics/
│   │   ├── __init__.py
│   │   ├── config.py                # Configuration management
│   │   ├── historian_connector.py    # Database connection layer
│   │   ├── metrics/
│   │   │   ├── rms_calculator.py     # RMS computation
│   │   │   └── health_engine.py      # Health metric aggregation
│   │   ├── thresholds/
│   │   │   └── threshold_engine.py   # Threshold comparison & alerting
│   │   ├── monitor.py                # Main monitoring loop
│   │   └── api.py                    # REST API for alerts
│   ├── tests/                        # Unit & integration tests
│   ├── requirements.txt
│   └── config.example.yaml
├── frontend/                         # Frontend (notification UI)
│   ├── components/
│   │   └── AlertNotification.jsx     # Alert display component
│   └── services/
│       └── alertApi.js               # API client
├── docs/                             # Documentation
│   ├── MEMO.md                       # Executive summary
│   ├── TAG_CATALOG.md                # PAFC & MMW PEMWE tags
│   └── API.md                        # API documentation
└── README.md
```

## Key Concepts

### RMS (Root Mean Square)
Measures the magnitude of vibration/pressure variations. Calculated as:
```
RMS = sqrt(mean(signal²))
```

### Health Metrics
- **Current RMS**: Recent RMS value
- **Trend**: Change in RMS over time
- **Status**: Healthy/Warning/Critical based on thresholds

### Threshold Strategy
- **Static**: Fixed upper/lower limits per component
- **Hysteresis**: Prevent state flicker (e.g., alert stays on until drops 10% below threshold)

### Alert Lifecycle
```
Healthy → Warning (metric exceeds threshold) → Critical → Acknowledged
```

## Systems Monitored

### PAFC (Trial)
- Valve health monitoring (vibration, pressure, temperature)
- Baseline thresholds derived from historical data

### MMW PEMWE (Planned)
- Candidate tags identified in Phase 1
- Implementation in Phase 2

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, APScheduler
- **Database**: Custom historian connector, SQLite for state
- **Frontend**: React/Vue with WebSocket alerts
- **Deployment**: Docker (optional)

## Configuration

Edit `config.yaml` to:
- Set historian database credentials
- Define component/tag mappings
- Configure threshold values per metric
- Set sampling frequency & alert sensitivity

Example:
```yaml
historian:
  type: custom_database
  connection_string: "your_connection_string"

components:
  PAFC_VALVE_01:
    metrics:
      vibration_rms:
        threshold_warning: 50
        threshold_critical: 75
        unit: "mm/s"
      pressure_variance:
        threshold_warning: 10
        threshold_critical: 20
        unit: "psi"

monitoring:
  interval_seconds: 60
  data_lookback_window: 300  # seconds
```

## Contributing

- Document new metrics in `docs/API.md`
- Add unit tests for new calculations
- Update `TAG_CATALOG.md` when adding systems
- Follow code style: Black formatter, flake8 linter

## Next Steps

1. **Phase 1**: Identify PAFC/MMW PEMWE valve tags
2. **Phase 2**: Implement core RMS engine & threshold logic
3. **Phase 3**: Run PAFC trial (validate accuracy)
4. **Phase 4**: Build frontend notification system
5. **Phase 5**: Prepare documentation & presentation

## References

- [RMS Analysis Guide](https://example.com)
- [Vibration-Based Prognostics](https://example.com)
- [Condition-Based Maintenance](https://example.com)

---

**Created**: 2026-06-08
**Team**: Equipment Monitoring Initiative
