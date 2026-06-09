# RMS Prognostics System - SETUP & DEPLOYMENT GUIDE

## 📋 PROJECT STRUCTURE

```
historian codebase/
├── backend/                              # Python backend
│   ├── prognostics/
│   │   ├── __init__.py
│   │   ├── config.py                    # Configuration management
│   │   ├── historian_connector.py        # Database interface
│   │   ├── monitor.py                   # Main monitoring loop
│   │   ├── api.py                       # FastAPI REST API
│   │   ├── metrics/
│   │   │   ├── rms_calculator.py         # RMS computation
│   │   │   └── health_engine.py          # Health metrics
│   │   └── thresholds/
│   │       └── threshold_engine.py       # Alerting logic
│   ├── tests/
│   │   ├── test_rms_calculator.py        # 12 unit tests
│   │   └── test_threshold_engine.py      # 14 unit tests
│   ├── main.py                          # CLI entry point
│   ├── requirements.txt                 # Python dependencies
│   └── config.example.yaml              # Configuration template
├── frontend/
│   ├── components/
│   │   ├── AlertNotification.jsx         # React component
│   │   └── AlertNotification.css         # Styling
│   └── services/
│       └── alertApi.js                   # API client
├── docs/
│   ├── API.md                           # API reference (22 endpoints)
│   ├── TAG_CATALOG.md                   # Equipment tags
│   ├── MEMO.md                          # Executive summary
│   └── GETTING_STARTED.md               # Setup guide
├── README.md                            # Project overview
└── PROJECT_STATUS.md                    # Deliverables summary
```

---

## 🚀 QUICK START (5 MINUTES)

### Step 1: Install Python & Dependencies

```bash
# Ensure Python 3.10+ is installed
python --version

# Navigate to backend
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Initialize Configuration

```bash
# Generate default config.yaml
python main.py --init-config

# Edit config.yaml with your settings
# - Update historian connection string
# - Keep PAFC valve definitions for trial
```

### Step 3: Run the System

```bash
# Option A: Start API server + monitoring (production)
python main.py --port 8000

# Option B: Monitor-only mode (background)
python main.py --monitor-only --interval 60
```

### Step 4: Test the API

```bash
# In another terminal, check system health
curl http://localhost:8000/health

# Get active alerts
curl http://localhost:8000/alerts

# View API documentation
# Open browser: http://localhost:8000/docs
```

---

## ⚙️ CONFIGURATION GUIDE

### Minimal Configuration (config.yaml)

```yaml
historian:
  type: custom_database
  connection_string: "your_connection_string_here"

monitoring:
  interval_seconds: 60
  data_lookback_window: 300

components:
  PAFC_VALVE_01:
    metrics:
      vibration_rms:
        tag_name: "PAFC.VALVE_01.VIBRATION"
        unit: "mm/s"
        warning: 50
        critical: 75
```

### Connection String Examples

**SQL Server**:
```
mssql+pyodbc://user:password@server/database?driver=ODBC+Driver+17+for+SQL+Server
```

**MySQL**:
```
mysql://user:password@localhost/historian_db
```

**PostgreSQL**:
```
postgresql://user:password@localhost/historian_db
```

**SQLite**:
```
sqlite:///path/to/database.db
```

### Complete Configuration

See `config.example.yaml` for full example with:
- All 3 PAFC valves
- 3 metrics per valve
- Threshold definitions
- Logging settings

---

## 🧪 TESTING

### Run Unit Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_rms_calculator.py -v

# Run with coverage
pytest tests/ --cov=prognostics
```

### Expected Output

```
test_rms_calculator.py::TestRMSCalculator::test_calculate_rms_simple PASSED
test_rms_calculator.py::TestRMSCalculator::test_calculate_rms_sine_wave PASSED
...
test_threshold_engine.py::TestThresholdEngine::test_evaluate_metric_healthy PASSED
...
26 passed in 0.45s
```

### Manual Testing

```bash
# Start API server
python main.py

# In another terminal:

# 1. Check health
curl http://localhost:8000/health

# 2. List components
curl http://localhost:8000/components

# 3. Get alerts (should be empty initially)
curl http://localhost:8000/alerts

# 4. View API docs
# http://localhost:8000/docs
```

---

## 📊 VERIFYING THE SYSTEM

### Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Configuration file created (`config.yaml`)
- [ ] Historian connection string configured
- [ ] Test database connection works
- [ ] Unit tests pass (`pytest tests/ -v`)
- [ ] API server starts without errors
- [ ] Health endpoint responds (`/health`)
- [ ] Components listed correctly (`/components`)
- [ ] No error logs during startup

### Common Issues

**"ModuleNotFoundError: No module named 'prognostics'"**
- Solution: Install from correct directory: `pip install -r requirements.txt`

**"Cannot connect to historian"**
- Solution: Verify connection string in config.yaml
- Test: `python -c "from prognostics.historian_connector import HistorianConnector; HistorianConnector('your_string').health_check()"`

**"Port 8000 already in use"**
- Solution: Use different port: `python main.py --port 8080`

**"No data for tag X"**
- Solution: Verify tag exists in historian database
- Update tag names in config.yaml to match historian

---

## 🔌 INTEGRATING WITH FRONTEND

### React Integration

```jsx
import AlertNotification from './components/AlertNotification';

function App() {
  return (
    <div className="app">
      <h1>Equipment Monitoring Dashboard</h1>
      <AlertNotification apiUrl="http://localhost:8000" />
    </div>
  );
}

export default App;
```

### API Service Usage

```javascript
import AlertApiService from './services/alertApi';

const api = new AlertApiService('http://localhost:8000');

// Get active alerts
const alerts = await api.getActiveAlerts();

// Acknowledge alert
await api.acknowledgeAlert('PAFC_VALVE_01');

// Get system health
const health = await api.getSystemHealth();

// Setup polling for real-time updates
const pollId = api.setupPolling((alert) => {
  console.log('New alert:', alert);
}, 5000);

// Clean up polling
clearInterval(pollId);
```

---

## 🐳 DOCKER DEPLOYMENT (Optional)

### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8000"]
```

### Build & Run

```bash
# Build image
docker build -t prognostics:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  --name prognostics \
  prognostics:latest

# Check logs
docker logs -f prognostics

# Stop container
docker stop prognostics
```

---

## 📈 PERFORMANCE TUNING

### Monitoring Interval

```yaml
monitoring:
  interval_seconds: 60  # Shorter = more frequent (higher CPU)
```

- 60 seconds (default): Balanced, good for most use cases
- 30 seconds: Near real-time, higher CPU load
- 300 seconds: Less frequent, lower CPU, slower alerts

### Data Lookback Window

```yaml
monitoring:
  data_lookback_window: 300  # Sample last 5 minutes
```

- Smaller window: Faster queries, less data to analyze
- Larger window: Better trend detection, slower queries

### Batch Query Optimization

Historian queries can be slow. Optimize by:
- Enabling database indexing on timestamp and tag_name columns
- Using connection pooling (future enhancement)
- Caching recent tag data (future enhancement)

---

## 📝 LOGGING

### Enable Debug Logging

```bash
python main.py --log-level DEBUG
```

### Log Files

- `prognostics.log` - Main log file (created automatically)
- Check for errors: `grep ERROR prognostics.log`
- Check for warnings: `grep WARNING prognostics.log`

### Example Log Output

```
2026-06-08 16:30:00,123 - prognostics.monitor - INFO - Prognostics monitor started
2026-06-08 16:30:05,456 - prognostics.historian_connector - DEBUG - Fetching tag data: PAFC.VALVE_01.VIBRATION
2026-06-08 16:30:06,789 - prognostics.thresholds.threshold_engine - WARNING - Alert generated: [WARNING] PAFC_VALVE_01 - vibration_rms at 55.2 (threshold: 50.0, +10.4%)
```

---

## 🔐 SECURITY CONSIDERATIONS

### Before Production Deployment

- [ ] Add API authentication (API keys or JWT)
- [ ] Enable HTTPS (use reverse proxy like nginx)
- [ ] Restrict database credentials (use environment variables)
- [ ] Implement rate limiting
- [ ] Add audit logging for alert acknowledgments
- [ ] Set up log aggregation and monitoring
- [ ] Review and test error handling
- [ ] Implement data encryption at rest

### Environment Variables

```bash
# Instead of hardcoding in config.yaml
export HISTORIAN_CONNECTION_STRING="your_connection_string"
export ALERT_WEBHOOK_URL="http://your-webhook.com"

# Reference in config.yaml:
historian:
  connection_string: ${HISTORIAN_CONNECTION_STRING}
```

---

## 🚨 PRODUCTION CHECKLIST

Before going live with Phase 2 trial:

- [ ] Configuration validated against historian database
- [ ] Unit tests passing (26/26)
- [ ] API endpoints responding correctly
- [ ] Historian connection stable
- [ ] 1-2 weeks baseline data collected
- [ ] Warning/critical thresholds set
- [ ] Alert accuracy tested (simulate failures)
- [ ] Frontend integrated and tested
- [ ] Operator training completed
- [ ] Monitoring alerts configured
- [ ] Backup and recovery procedures documented
- [ ] On-call runbook prepared

---

## 📞 SUPPORT & TROUBLESHOOTING

### FAQ

**Q: How do I change the monitoring interval?**
A: Edit `config.yaml`: `monitoring: interval_seconds: 30`

**Q: Can I monitor multiple systems?**
A: Yes! Add more components to the `components:` section in config.yaml

**Q: How do I update thresholds?**
A: Edit warning/critical values in config.yaml, restart the system

**Q: Are there any data retention limits?**
A: Currently unlimited. Add archival logic in Phase 3.

**Q: Can I run this in production?**
A: Yes, but add authentication and HTTPS first.

### Getting Help

- See `docs/API.md` for API reference
- See `docs/GETTING_STARTED.md` for configuration
- See `docs/TAG_CATALOG.md` for equipment tags
- Check `prognostics.log` for error messages
- View API documentation: http://localhost:8000/docs

---

## 🎯 SUCCESS INDICATORS

Your setup is successful when:

1. ✅ API server starts without errors
2. ✅ Health endpoint returns `"status": "healthy"`
3. ✅ All 26 unit tests pass
4. ✅ Components are listed correctly
5. ✅ Historian connection is working
6. ✅ No errors in `prognostics.log`
7. ✅ Frontend alerts display correctly
8. ✅ Thresholds configured for PAFC valves

---

## 📅 NEXT STEPS

1. **This Week**: Setup and configuration
2. **Week 1-2**: Baseline characterization on PAFC
3. **Week 3-6**: Live trial monitoring
4. **Week 7-8**: Expand to MMW PEMWE
5. **Week 9-10**: Frontend deployment
6. **Week 11-12**: Handoff to operations

---

**Created**: June 8, 2026  
**Version**: 0.1.0 (MVP)  
**Status**: Ready for Phase 2 Trial

For updates and latest documentation, see PROJECT_STATUS.md
