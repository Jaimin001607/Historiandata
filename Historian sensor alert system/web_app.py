import json
import logging
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import plotly.utils
from flask import Flask, jsonify, render_template_string, request

from training_pipeline import RMSTrainingPipeline

DATA_FOLDER = "historian_data"
MODELS_DIR = "trained_models"

app = Flask(__name__)

pipeline = RMSTrainingPipeline(output_dir=MODELS_DIR, data_folder=DATA_FOLDER)
try:
    pipeline.load_models(MODELS_DIR)
except Exception:
    app.logger.info("No saved models found.")

try:
    _files = pipeline.scan_data_folder()
except (FileNotFoundError, ValueError) as _e:
    app.logger.warning(str(_e))
    _files = []

if _files:
    try:
        consolidated_df = pipeline.load_consolidated_cache(csv_files=_files)
        print(f"\n  Loaded from cache: {len(consolidated_df)} records")
    except Exception as _cache_miss:
        app.logger.info("Cache miss (%s) — parsing CSV files…", _cache_miss)
        consolidated_df = pipeline.load_and_consolidate(_files)
        pipeline.save_consolidated_cache(consolidated_df)
    consolidated_df["component_id"] = consolidated_df["component_id"].astype(str)
    print(f"  Records: {len(consolidated_df)}")
    print(f"  Plants:  {consolidated_df['component_id'].nunique()}")
    print(f"  Range:   {consolidated_df['timestamp'].min().date()} -> {consolidated_df['timestamp'].max().date()}\n")
else:
    consolidated_df = pd.DataFrame(columns=["timestamp", "component_id"])
    app.logger.warning("No CSV files in '%s'. Add files and restart.", DATA_FOLDER)


def _sensor_cols():
    return pipeline.client.get_sensor_columns(consolidated_df)


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(_HTML)


@app.route("/api/info")
def api_info():
    if consolidated_df.empty:
        return jsonify({"records": 0, "plants": 0, "sensors": 0, "start": None, "end": None})
    return jsonify({
        "records": len(consolidated_df),
        "plants": int(consolidated_df["component_id"].nunique()),
        "sensors": len(_sensor_cols()),
        "start": str(consolidated_df["timestamp"].min().date()),
        "end": str(consolidated_df["timestamp"].max().date()),
    })


@app.route("/api/sensors")
def api_sensors():
    return jsonify(sorted(_sensor_cols()))


@app.route("/api/plants")
def api_plants():
    if consolidated_df.empty:
        return jsonify([])
    plants = sorted(consolidated_df["component_id"].dropna().unique().tolist())
    return jsonify(plants)


@app.route("/plot")
def plot():
    sensor = request.args.get("sensor", "").strip()
    plant = request.args.get("plant", "ALL").strip()
    last_days = request.args.get("last_days", type=int)

    if not sensor:
        return jsonify({"error": "missing sensor"}), 400
    if sensor not in consolidated_df.columns:
        return jsonify({"error": "sensor not found"}), 404

    df = consolidated_df.copy()
    if last_days:
        cutoff = datetime.now() - timedelta(days=last_days)
        df = df[df["timestamp"] >= cutoff]
    if df.empty:
        return jsonify({"error": "no data in selected range"}), 404

    df = df[["timestamp", "component_id", sensor]].dropna(subset=[sensor])
    if df.empty:
        return jsonify({"error": "no data for sensor"}), 404

    # Fleet aggregate: mean and std across all plants per timestamp
    agg = (
        df.groupby("timestamp")[sensor]
        .agg(fleet_mean="mean", fleet_std="std")
        .reset_index()
        .sort_values("timestamp")
    )
    agg["fleet_std"] = agg["fleet_std"].fillna(0)

    fig = go.Figure()

    # Deviation band (mean ± 1 std)
    fig.add_trace(go.Scatter(
        x=pd.concat([agg["timestamp"], agg["timestamp"][::-1]]),
        y=pd.concat([agg["fleet_mean"] + agg["fleet_std"],
                     (agg["fleet_mean"] - agg["fleet_std"])[::-1]]),
        fill="toself",
        fillcolor="rgba(37,99,235,0.12)",
        line=dict(color="rgba(0,0,0,0)"),
        hoverinfo="skip",
        name="+/- 1 Std Dev",
        showlegend=True,
    ))

    # Fleet mean line
    fig.add_trace(go.Scatter(
        x=agg["timestamp"],
        y=agg["fleet_mean"],
        mode="lines",
        name="Fleet Average",
        line=dict(color="#2563eb", width=2),
    ))

    # Single-plant overlay
    if plant and plant != "ALL":
        pdf = df[df["component_id"] == plant].sort_values("timestamp")
        if not pdf.empty:
            fig.add_trace(go.Scatter(
                x=pdf["timestamp"],
                y=pdf[sensor].astype(float),
                mode="lines+markers",
                name=f"Plant {plant}",
                line=dict(color="#f59e0b", width=1.5),
                marker=dict(size=3),
            ))

    fig.update_layout(
        title=dict(text=f"{sensor}  —  Fleet Historian", font=dict(size=16)),
        xaxis_title="Timestamp",
        yaxis_title=sensor,
        template="plotly_white",
        height=500,
        margin=dict(l=60, r=30, t=60, b=50),
        legend=dict(orientation="h", y=1.1),
        hovermode="x unified",
    )

    return jsonify(json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig)))


@app.route("/train", methods=["POST"])
def train():
    from sensor_prognostic_model import SensorPrognosticModel
    sensor = request.form.get("sensor", "").strip()
    plant = request.form.get("plant", "ALL").strip()
    min_samples = int(request.form.get("min_samples", 30))

    if not sensor:
        return "Missing sensor", 400
    if sensor not in consolidated_df.columns:
        return "Sensor not found", 404

    df = consolidated_df.copy()
    if plant and plant != "ALL":
        df = df[df["component_id"] == plant]

    try:
        label = plant if plant != "ALL" else "fleet"
        model = SensorPrognosticModel(label, app.logger)
        profile = model.train_sensor(sensor, df, min_samples=min_samples)
        pipeline.models[f"{label}__{sensor}"] = model
        pipeline.save_models(save_dir=MODELS_DIR)
        return f"Trained baseline for {label}:{sensor} ({profile['n_samples']} samples)"
    except Exception as exc:
        return f"Training failed: {exc}", 500


# ── HTML ─────────────────────────────────────────────────────────────────────

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Historian Sensor Explorer</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           background: #f0f2f5; color: #1e2533; min-height: 100vh; }

    header {
      background: #1a2340; color: #fff;
      padding: 14px 28px;
      display: flex; align-items: center; justify-content: space-between; gap: 16px;
      flex-wrap: wrap;
    }
    header h1 { font-size: 1.05rem; font-weight: 700; letter-spacing: 0.04em; }
    .stats { display: flex; gap: 24px; flex-wrap: wrap; }
    .stat { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; opacity: 0.7; }
    .stat strong { display: block; font-size: 0.95rem; opacity: 1; margin-top: 2px; letter-spacing: 0; }

    .controls {
      background: #fff; border-bottom: 1px solid #dde1e9;
      padding: 14px 28px; display: flex; align-items: flex-end; gap: 16px; flex-wrap: wrap;
    }
    .field { display: flex; flex-direction: column; gap: 5px; }
    .field label { font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
                   letter-spacing: 0.06em; color: #6b7380; }
    .field select, .field input {
      padding: 7px 11px; border: 1px solid #cdd1da; border-radius: 7px;
      font-size: 0.875rem; background: #fff; color: #1e2533;
      outline: none; transition: border-color 0.15s;
    }
    .field select { min-width: 230px; }
    .field input  { min-width: 130px; }
    .field select:focus, .field input:focus { border-color: #2563eb; }

    .btn {
      padding: 7px 22px; border: none; border-radius: 7px;
      font-size: 0.875rem; font-weight: 600; cursor: pointer; align-self: flex-end;
      transition: background 0.15s;
    }
    .btn-primary   { background: #2563eb; color: #fff; }
    .btn-primary:hover:not(:disabled)   { background: #1d4ed8; }
    .btn-secondary { background: #e8eaf0; color: #1e2533; }
    .btn-secondary:hover:not(:disabled) { background: #d8dbe6; }
    .btn:disabled  { background: #b0b8c5; color: #fff; cursor: default; }

    #status {
      padding: 10px 28px; font-size: 0.82rem; color: #6b7380;
      min-height: 36px; display: flex; align-items: center; gap: 8px;
    }
    #status.error   { color: #dc2626; }
    #status.success { color: #16a34a; }
    .spinner {
      width: 13px; height: 13px; border: 2px solid #ccc; border-top-color: #2563eb;
      border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    #chart-wrap { padding: 0 16px 24px; }
    #chart { background: #fff; border-radius: 10px; border: 1px solid #dde1e9; min-height: 60px; }
  </style>
</head>
<body>

<header>
  <h1>Historian Sensor Explorer</h1>
  <div class="stats">
    <div class="stat">Records<strong id="s-records">—</strong></div>
    <div class="stat">Plants<strong id="s-plants">—</strong></div>
    <div class="stat">Sensors<strong id="s-sensors">—</strong></div>
    <div class="stat">Date Range<strong id="s-range">—</strong></div>
  </div>
</header>

<div class="controls">
  <div class="field">
    <label>Sensor</label>
    <select id="sens" onchange="onSensorChange()">
      <option value="">— select sensor —</option>
    </select>
  </div>
  <div class="field">
    <label>Plant (optional filter)</label>
    <select id="plant">
      <option value="ALL">All Plants (Fleet Average)</option>
    </select>
  </div>
  <div class="field">
    <label>Last N Days</label>
    <input id="days" type="number" min="1" placeholder="All time">
  </div>
  <button class="btn btn-primary"   id="plotBtn"  onclick="loadChart()"     disabled>Plot</button>
  <button class="btn btn-secondary" id="trainBtn" onclick="trainBaseline()" disabled>Train Baseline</button>
</div>

<div id="status"></div>
<div id="chart-wrap"><div id="chart"></div></div>

<script>
const $ = id => document.getElementById(id);

async function apiFetch(url, opts) {
  const r = await fetch(url, opts);
  const ct = r.headers.get('content-type') || '';
  const body = ct.includes('json') ? await r.json() : await r.text();
  if (!r.ok) throw new Error((body && body.error) || body || r.statusText);
  return body;
}

function status(msg, cls, showSpinner) {
  const el = $('status');
  el.className = cls || '';
  el.innerHTML = '';
  if (showSpinner) { const s = document.createElement('div'); s.className = 'spinner'; el.appendChild(s); }
  if (msg) el.appendChild(document.createTextNode(msg));
}

async function init() {
  status('Loading data...', '', true);
  try {
    const info = await apiFetch('/api/info');
    $('s-records').textContent  = info.records.toLocaleString();
    $('s-plants').textContent   = info.plants;
    $('s-sensors').textContent  = info.sensors;
    $('s-range').textContent    = info.start ? info.start + ' to ' + info.end : 'No data';

    if (info.records === 0) {
      status('No CSV files found in historian_data/. Add files and restart.', 'error');
      return;
    }

    const [sensors, plants] = await Promise.all([
      apiFetch('/api/sensors'),
      apiFetch('/api/plants'),
    ]);

    const sSel = $('sens');
    sensors.forEach(s => sSel.appendChild(new Option(s, s)));

    const pSel = $('plant');
    plants.forEach(p => pSel.appendChild(new Option('Plant ' + p, p)));

    status('Select a sensor and click Plot. Use the plant filter to overlay a single plant against the fleet average.');
  } catch (e) {
    status('Failed to initialise: ' + e.message, 'error');
  }
}

function onSensorChange() {
  const has = !!$('sens').value;
  $('plotBtn').disabled  = !has;
  $('trainBtn').disabled = !has;
}

async function loadChart() {
  const sens  = $('sens').value;
  const plant = $('plant').value;
  const days  = $('days').value;
  if (!sens) return;

  status('Loading chart...', '', true);
  $('plotBtn').disabled = true;

  try {
    let url = '/plot?sensor=' + encodeURIComponent(sens)
            + '&plant='  + encodeURIComponent(plant);
    if (days) url += '&last_days=' + days;
    const fig = await apiFetch(url);
    Plotly.react('chart', fig.data, fig.layout, { responsive: true });
    status('');
  } catch (e) {
    status('Chart error: ' + e.message, 'error');
  } finally {
    $('plotBtn').disabled = false;
  }
}

async function trainBaseline() {
  const sens  = $('sens').value;
  const plant = $('plant').value;
  if (!sens) return;
  const minSamples = prompt('Minimum samples to train (e.g. 30):', '30');
  if (minSamples === null) return;

  status('Training...', '', true);
  $('trainBtn').disabled = true;
  try {
    const body = new URLSearchParams({ sensor: sens, plant: plant, min_samples: minSamples || '30' });
    const msg = await apiFetch('/train', { method: 'POST', body });
    status(msg, 'success');
  } catch (e) {
    status('Training failed: ' + e.message, 'error');
  } finally {
    $('trainBtn').disabled = false;
  }
}

init();
</script>
</body>
</html>"""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("\n  Dashboard -> http://localhost:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
