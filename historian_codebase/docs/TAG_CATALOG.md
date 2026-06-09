# Tag Catalog for RMS Prognostics

This document catalogs all available sensor tags from equipment systems being monitored.

## PAFC (Proton Exchange Membrane Fuel Cell) System

### Overview
The PAFC system has 3 monitored valves with vibration, pressure, and temperature sensors.

### Valve 01
**Component ID**: `PAFC_VALVE_01`  
**Description**: Primary fuel inlet valve

| Metric | Tag Name | Unit | Type | Baseline | Warning | Critical |
|--------|----------|------|------|----------|---------|----------|
| Vibration RMS | `PAFC.VALVE_01.VIBRATION` | mm/s | Continuous | 30-40 | 50 | 75 |
| Pressure | `PAFC.VALVE_01.PRESSURE` | psi | Continuous | 0-10 | 10 | 20 |
| Temperature | `PAFC.VALVE_01.TEMPERATURE` | °C | Continuous | 20-40 | 70 | 85 |
| Flow Rate | `PAFC.VALVE_01.FLOW` | L/min | Continuous | - | - | - |
| Position | `PAFC.VALVE_01.POSITION` | % | Discrete | 0-100 | - | - |

### Valve 02
**Component ID**: `PAFC_VALVE_02`  
**Description**: Secondary fuel inlet valve

| Metric | Tag Name | Unit | Type | Baseline | Warning | Critical |
|--------|----------|------|------|----------|---------|----------|
| Vibration RMS | `PAFC.VALVE_02.VIBRATION` | mm/s | Continuous | 30-40 | 50 | 75 |
| Pressure | `PAFC.VALVE_02.PRESSURE` | psi | Continuous | 0-10 | 10 | 20 |
| Temperature | `PAFC.VALVE_02.TEMPERATURE` | °C | Continuous | 20-40 | 70 | 85 |
| Flow Rate | `PAFC.VALVE_02.FLOW` | L/min | Continuous | - | - | - |
| Position | `PAFC.VALVE_02.POSITION` | % | Discrete | 0-100 | - | - |

### Valve 03
**Component ID**: `PAFC_VALVE_03`  
**Description**: Exhaust outlet valve

| Metric | Tag Name | Unit | Type | Baseline | Warning | Critical |
|--------|----------|------|------|----------|---------|----------|
| Vibration RMS | `PAFC.VALVE_03.VIBRATION` | mm/s | Continuous | 30-40 | 50 | 75 |
| Pressure | `PAFC.VALVE_03.PRESSURE` | psi | Continuous | 0-10 | 10 | 20 |
| Temperature | `PAFC.VALVE_03.TEMPERATURE` | °C | Continuous | 20-40 | 70 | 85 |
| Flow Rate | `PAFC.VALVE_03.FLOW` | L/min | Continuous | - | - | - |
| Position | `PAFC.VALVE_03.POSITION` | % | Discrete | 0-100 | - | - |

### Data Collection Notes
- **Sampling Rate**: Historian samples vibration at 1 kHz, downsampled for storage
- **Aggregation**: RMS calculated over 60-second windows
- **Retention**: Historical data retained for 12 months
- **Quality**: All sensors are redundant; fail-safe on primary sensor loss

---

## MMW PEMWE (Membrane Module Water Electrolysis) System

### Candidate Tags (Phase 2)

To be populated during Phase 1 tag identification.

### Expected Components
- Water inlet valve
- Water outlet valve
- Hydrogen outlet valve
- Oxygen outlet valve
- Pressure regulator
- Temperature control valve

### Data Sources
- Historian database: `PEMWE_HISTORIAN`
- Real-time API: `PEMWE_REALTIME_API` (fallback)

---

## Tag Naming Convention

**Pattern**: `{SYSTEM}.{COMPONENT}.{METRIC}`

**Examples**:
- `PAFC.VALVE_01.VIBRATION` - PAFC system, Valve 01, Vibration metric
- `PEMWE.PUMP_01.PRESSURE` - PEMWE system, Pump 01, Pressure metric

**Metric Abbreviations**:
- `VIBRATION` - Vibration RMS
- `PRESSURE` - Pressure reading
- `TEMPERATURE` - Temperature reading
- `FLOW` - Flow rate
- `POSITION` - Valve/actuator position
- `CURRENT` - Motor/pump current draw
- `FAULT` - Fault/alarm flag

---

## Data Quality Guidelines

### Good Data Indicators
- Consistent timestamp intervals
- Values within sensor range (no clipping)
- Minimal noise (reasonable standard deviation)
- No gaps > 5 minutes

### Warning Signs
- Frozen values (no change over time)
- Outliers beyond 5σ standard deviation
- Negative pressure or impossible values
- Frequent gaps in data

---

## Adding New Tags

To add a new sensor tag:

1. Update this catalog with tag metadata
2. Add corresponding entry in `config.yaml` components section
3. Run baseline characterization (1-2 weeks of normal operation)
4. Set warning/critical thresholds from baseline + 1-2 standard deviations
5. Test alert generation with synthetic data
6. Document any special handling (e.g., filtering, preprocessing)

---

**Last Updated**: 2026-06-08  
**Phase**: 1 (PAFC tags identified, MMW PEMWE pending)
