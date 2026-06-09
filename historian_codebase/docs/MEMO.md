# MEMO: RMS-Based Equipment Prognostics System

**TO**: Equipment Maintenance Team  
**FROM**: Monitoring Engineering Team  
**DATE**: June 8, 2026  
**SUBJECT**: Real-Time Condition-Based Maintenance via RMS Prognostics  

---

## EXECUTIVE SUMMARY

This memo outlines the implementation of an RMS (Root Mean Square)-based prognostics engine for predictive equipment maintenance. The system monitors equipment health in real-time by analyzing sensor vibration, pressure, and temperature data, enabling maintenance teams to replace components before failure rather than after.

**Expected Benefits**:
- **Reduced Unplanned Downtime**: 20-30% reduction in equipment failures
- **Extended Equipment Life**: Replace components at optimal time vs. failure
- **Cost Savings**: Preventive maintenance costs < reactive emergency repairs
- **Operational Visibility**: Real-time health dashboard and alerts

---

## BACKGROUND

### Current State
Equipment maintenance is currently **reactive**:
- Components run until failure
- Maintenance occurs after breakdown
- Leads to unexpected downtime and safety risks
- Difficult to predict when replacement is needed

### Proposed Solution
**Condition-Based Maintenance** (CBM) using RMS prognostics:
- Continuous monitoring of equipment health metrics
- Early warning system before component failure
- Data-driven maintenance scheduling
- Optimized equipment replacement timing

---

## TECHNICAL APPROACH

### RMS (Root Mean Square) Analysis

RMS measures the magnitude of a signal's vibration/oscillation:

```
RMS = √(mean(signal²))
```

**Why RMS?**
- Captures overall signal magnitude (not just peak values)
- Sensitive to degradation in bearing friction, lubrication loss, wear
- Industry standard for vibration analysis
- Easy to compute and interpret

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Historian Database                         │
│              (Time-series sensor data storage)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        v                             v
┌──────────────────┐        ┌─────────────────────┐
│ Data Sampling    │        │ Metric Calculation  │
│ (Every 60 sec)   │        │ (RMS computation)   │
└──────────────────┘        └─────────────────────┘
        │                             │
        └──────────────┬──────────────┘
                       │
                       v
        ┌──────────────────────────┐
        │  Threshold Evaluation    │
        │  (Alert generation)      │
        └──────────────────────────┘
                       │
                       v
        ┌──────────────────────────┐
        │  Frontend Notification   │
        │  (Real-time alerts)      │
        └──────────────────────────┘
```

### Key Features

1. **Real-Time Monitoring**: Samples data every 60 seconds (can scale to faster)
2. **Smart Thresholds**: Warning/Critical levels with hysteresis to prevent alert flicker
3. **Health Aggregation**: Combines multiple metrics (vibration, pressure, temp) into overall status
4. **Trend Analysis**: Tracks degradation rate and predicts time-to-failure
5. **Alert Management**: Structured alerts with acknowledgment and history tracking

---

## TRIAL IMPLEMENTATION: PAFC SYSTEM

### Scope

The system is first deployed on the **PAFC (Proton Exchange Membrane Fuel Cell)** system with 3 monitored valves:
- **PAFC_VALVE_01**: Primary fuel inlet valve
- **PAFC_VALVE_02**: Secondary fuel inlet valve  
- **PAFC_VALVE_03**: Exhaust outlet valve

### Monitored Metrics

Per valve, we track 3 health indicators:

| Metric | Sensor | Normal Range | Warning | Critical |
|--------|--------|--------------|---------|----------|
| **Vibration RMS** | Accelerometer | 30-40 mm/s | 50 | 75 |
| **Pressure Variance** | Pressure sensor | 0-10 psi | 10 | 20 |
| **Temperature** | Thermocouple | 20-40°C | 70 | 85 |

### Expected Outcomes

**Phase 1 - Setup & Validation** (Weeks 1-2):
- [ ] Confirm data availability in historian
- [ ] Validate RMS calculations against manual samples
- [ ] Establish baseline thresholds (±1-2σ from normal operation)
- [ ] Test alert generation with synthetic data

**Phase 2 - Live Trial** (Weeks 3-6):
- [ ] Monitor PAFC valves in production
- [ ] Validate threshold accuracy (minimize false positives)
- [ ] Collect degradation patterns for ML training (future)
- [ ] Gather operator feedback on alert usefulness

**Phase 3 - Expansion** (Weeks 7+):
- [ ] Add MMW PEMWE system monitoring
- [ ] Enhance with predictive failure models
- [ ] Integrate with maintenance scheduling system
- [ ] Deploy to operations team dashboard

### Success Metrics

1. **Accuracy**: >95% alert precision (minimize false positives)
2. **Response Time**: <2 seconds from threshold breach to notification
3. **Availability**: 99%+ system uptime
4. **Adoption**: >80% operator engagement within 30 days

---

## TECHNOLOGY STACK

**Backend**:
- Python 3.10+ (scientific computing, data analysis)
- FastAPI (REST API, real-time alerts)
- APScheduler (monitoring cycle scheduling)
- NumPy/SciPy (RMS and statistical calculations)

**Database**:
- Custom Historian (existing data source)
- SQLite (current component state & alert history)

**Frontend**:
- React or Vue.js (notification UI)
- WebSocket/polling (real-time updates)

**Deployment**:
- Docker (containerization, easy scaling)
- Kubernetes (optional for production clustering)

---

## IMPLEMENTATION ROADMAP

```
Week 1-2:    Phase 1 - Setup, data validation, threshold tuning
Week 3-6:    Phase 2 - PAFC live trial, feedback, refinement
Week 7-8:    Phase 3 - MMW PEMWE tag identification
Week 9-10:   Phase 4 - Frontend integration, operator training
Week 11-12:  Phase 5 - Documentation, presentation, handoff
```

---

## RISKS & MITIGATION

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Historian connection instability | Missed alerts | Health monitoring, fallback to snapshot mode |
| Threshold tuning (false positives) | Operator alert fatigue | Conservative thresholds, 2-week validation period |
| Data quality issues (gaps, noise) | Inaccurate metrics | Preprocessing filters, outlier detection |
| Integration delay | Project timeline slip | Early communication with data team |

---

## BUDGET ESTIMATE

| Item | Estimate |
|------|----------|
| Development (engineering time) | 320 hours |
| Testing & validation | 80 hours |
| Documentation & training | 40 hours |
| Infrastructure (hardware, licenses) | Minimal (existing) |
| **Total** | **~$32K-48K** |

---

## RECOMMENDATIONS

1. **Immediate** (This week):
   - Approve RMS prognostics approach
   - Schedule historian access & tag review meeting
   - Assign backend engineer to Phase 1 setup

2. **Near-term** (Weeks 1-4):
   - Conduct PAFC baseline characterization
   - Validate threshold assumptions with real data
   - Build frontend notification UI in parallel

3. **Medium-term** (Weeks 5-12):
   - Expand to MMW PEMWE system
   - Integrate with maintenance scheduling (CMMS)
   - Develop predictive failure models (ML)

4. **Long-term** (3-6 months):
   - Deploy to all critical equipment systems
   - Implement automated maintenance task generation
   - Integrate with autonomous inventory management

---

## NEXT STEPS

- [ ] Review and approve this approach
- [ ] Schedule historian access
- [ ] Finalize PAFC component list and sensor tags
- [ ] Kick-off development (Phase 1)
- [ ] Weekly progress updates

---

**Appendices**:
- A: Detailed technical specifications (see `docs/`)
- B: API documentation (see `docs/API.md`)
- C: Tag catalog with all monitored sensors (see `docs/TAG_CATALOG.md`)
- D: Code repository (see `backend/` and `frontend/` directories)

---

**Questions?** Contact Equipment Monitoring Engineering Team

**Distribution**: Operations, Maintenance, Engineering Leadership
