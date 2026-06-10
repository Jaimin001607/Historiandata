import json
import logging
from datetime import datetime, timedelta

import plotly.graph_objects as go
import plotly.utils
from flask import Flask, jsonify, render_template_string, request

from training_pipeline import RMSTrainingPipeline
from sensor_prognostic_model import SensorPrognosticModel

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
    consolidated_df = pipeline.load_and_consolidate(_files)
    print(f"\n  Total records: {len(consolidated_df)}")
    print(f"  Date range:    {consolidated_df['timestamp'].min().date()} → {consolidated_df['timestamp'].max().date()}\n")
else:
    import pandas as pd
    consolidated_df = pd.DataFrame(columns=["timestamp", "component_id"])
    app.logger.warning("No CSV files in '%s'. Add files and restart.", DATA_FOLDER)


# ── routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(_HTML)


@app.route("/api/info")
def api_info():
    if consolidated_df.empty:
        return jsonify({"records": 0, "components": 0, "start": None, "end": None})
    return jsonify({
        "records": len(consolidated_df),
        "components": int(consolidated_df["component_id"].nunique()),
        "start": str(consolidated_df["timestamp"].min().date()),
        "end": str(consolidated_df["timestamp"].max().date()),
    })


@app.route("/sensors")
def sensors():
    comp = request.args.get("component", "").strip()
    if not comp:
        return jsonify([])
    df = consolidated_df[consolidated_df["component_id"].astype(str) == comp]
    return jsonify(pipeline.client.get_sensor_columns(df))


@app.route("/plot")
def plot():
    comp = request.args.get("component", "").strip()
    sensor = request.args.get("sensor", "").strip()
    last_days = request.args.get("last_days", type=int)
    overlay = request.args.get("overlay", "1") == "1"

    if not comp or not sensor:
        return jsonify({"error": "missing component or sensor"}), 400

    df = consolidated_df[consolidated_df["component_id"].astype(str) == comp].copy()
    if df.empty:
        return jsonify({"error": "no data for component"}), 404
    if sensor not in df.columns:
        return jsonify({"error": "sensor not found"}), 404

    if last_days:
        cutoff = datetime.now() - timedelta(days=last_days)
        df = df[df["timestamp"] >= cutoff]

    df = df[["timestamp", sensor]].dropna(subset=[sensor]).sort_values("timestamp")
    if df.empty:
        return jsonify({"error": "no data in selected range"}), 404

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df[sensor].astype(float),
        mode="lines+markers",
        name=sensor,
        marker=dict(size=4),
        line=dict(width=1.5),
    ))

    if overlay:
        key = f"{comp}__{sensor}"
        if key in pipeline.models:
            model = pipeline.models[key]
            profiles = getattr(model, "baseline_profiles", {})
            if sensor in profiles:
                mean = profiles[sensor].get("mean")
                std = profiles[sensor].get("std")
                if mean is not None:
                    fig.add_hline(
                        y=mean, line_dash="dash", line_color="red",
                        annotation_text=f"Baseline μ={mean:.2f}",
                    )
                if mean is not None and std is not None:
                    fig.add_hrect(
                        y0=mean - std, y1=mean + std,
                        fillcolor="red", opacity=0.07, line_width=0,
                    )

    fig.update_layout(
        title=dict(text=f"{comp} — {sensor}", font=dict(size=16)),
        xaxis_title="Timestamp",
        yaxis_title=sensor,
        template="plotly_white",
        height=480,
        margin=dict(l=60, r=30, t=60, b=50),
        legend=dict(orientation="h", y=1.08),
    )

    return jsonify(json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig)))


@app.route("/train", methods=["POST"])
def train():
    comp = request.form.get("component", "").strip()
    sensor = request.form.get("sensor", "").strip()
    min_samples = int(request.form.get("min_samples", 30))
    history_days = request.form.get("history_days")
    history_days = int(history_days) if history_days else None

    if not comp or not sensor:
        return "Missing component or sensor", 400

    df = consolidated_df[consolidated_df["component_id"].astype(str) == comp].copy()
    if history_days:
        cutoff = datetime.now() - timedelta(days=history_days)
        df = df[df["timestamp"] >= cutoff]

    if sensor not in df.columns:
        return "Sensor not found", 404

    try:
        model = SensorPrognosticModel(comp, app.logger)
        profile = model.train_sensor(sensor, df, min_samples=min_samples)
        pipeline.models[f"{comp}__{sensor}"] = model
        pipeline.save_models(save_dir=MODELS_DIR)
        return f"Trained baseline for {comp}:{sensor} ({profile['n_samples']} samples)"
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
    }
    header h1 { font-size: 1.05rem; font-weight: 700; letter-spacing: 0.04em; white-space: nowrap; }
    .stats { display: flex; gap: 28px; }
    .stat { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; opacity: 0.7; }
    .stat strong { display: block; font-size: 0.95rem; opacity: 1; margin-top: 2px; letter-spacing: 0; }

    .controls {
      background: #fff; border-bottom: 1px solid #dde1e9;
      padding: 14px 28px; display: flex; align-items: flex-end; gap: 18px; flex-wrap: wrap;
    }
    .field { display: flex; flex-direction: column; gap: 5px; }
    .field label { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #6b7380; }
    .field select, .field input {
      padding: 7px 11px; border: 1px solid #cdd1da; border-radius: 7px;
      font-size: 0.875rem; background: #fff; color: #1e2533; min-width: 210px;
      outline: none; transition: border-color 0.15s;
    }
    .field select:focus, .field input:focus { border-color: #2563eb; }
    .field input { min-width: 130px; }
    .chk-field { display: flex; align-items: center; gap: 7px; align-self: flex-end;
                 font-size: 0.875rem; padding-bottom: 8px; }
    .chk-field input { min-width: unset; width: 15px; height: 15px; }

    .btn {
      padding: 7px 22px; border: none; border-radius: 7px;
      font-size: 0.875rem; font-weight: 600; cursor: pointer; align-self: flex-end;
      transition: background 0.15s;
    }
    .btn-primary { background: #2563eb; color: #fff; }
    .btn-primary:hover:not(:disabled) { background: #1d4ed8; }
    .btn-secondary { background: #e8eaf0; color: #1e2533; }
    .btn-secondary:hover:not(:disabled) { background: #d8dbe6; }
    .btn:disabled { background: #b0b8c5; color: #fff; cursor: default; }

    #status {
      padding: 10px 28px; font-size: 0.82rem; color: #6b7380;
      min-height: 36px; display: flex; align-items: center; gap: 8px;
    }
    #status.error { color: #dc2626; }
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
    <div class="stat">Components<strong id="s-components">—</strong></div>
    <div class="stat">Date Range<strong id="s-range">—</strong></div>
  </div>
</header>

<div class="controls">
  <div class="field">
    <label>Component / Location</label>
    <select id="comp" onchange="onCompChange()">
      <option value="">— select —</option>
    </select>
  </div>
  <div class="field">
    <label>Sensor</label>
    <select id="sens">
      <option value="">— select —</option>
    </select>
  </div>
  <div class="field">
    <label>Last N Days</label>
    <input id="days" type="number" min="1" placeholder="All time">
  </div>
  <div class="chk-field">
    <input id="overlay" type="checkbox" checked>
    <label for="overlay">Overlay baseline</label>
  </div>
  <button class="btn btn-primary" id="plotBtn" onclick="loadChart()" disabled>Plot</button>
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
  status('Loading data…', '', true);
  try {
    const info = await apiFetch('/api/info');
    $('s-records').textContent = info.records.toLocaleString();
    $('s-components').textContent = info.components;
    $('s-range').textContent = info.start ? info.start + ' → ' + info.end : 'No data';

    if (info.records === 0) {
      status('No CSV files found in historian_data/. Add files and restart the server.', 'error');
      return;
    }

    const comps = await apiFetch('/sensors?component=__list__').catch(() => null);
    // get component list from the consolidated df via components endpoint
    const compList = await apiFetch('/api/components').catch(async () => {
      // fallback: try to derive from sensors route
      return [];
    });
    const sel = $('comp');
    compList.forEach(c => sel.appendChild(new Option(c, c)));
    status('Select a component and sensor, then click Plot.');
  } catch (e) {
    status('Failed to initialise: ' + e.message, 'error');
  }
}

async function onCompChange() {
  const comp = $('comp').value;
  const sel = $('sens');
  sel.innerHTML = '<option value="">— select —</option>';
  $('plotBtn').disabled = true;
  $('trainBtn').disabled = true;
  if (!comp) { status('Select a component.'); return; }

  status('Loading sensors…', '', true);
  try {
    const sensors = await apiFetch('/sensors?component=' + encodeURIComponent(comp));
    sensors.forEach(s => sel.appendChild(new Option(s, s)));
    sel.onchange = () => {
      const has = !!sel.value;
      $('plotBtn').disabled = !has;
      $('trainBtn').disabled = !has;
    };
    status('Select a sensor, then click Plot.');
  } catch (e) {
    status('Could not load sensors: ' + e.message, 'error');
  }
}

async function loadChart() {
  const comp = $('comp').value, sens = $('sens').value;
  const days = $('days').value;
  const overlay = $('overlay').checked ? '1' : '0';
  if (!comp || !sens) return;

  status('Loading chart…', '', true);
  $('plotBtn').disabled = true;

  try {
    let url = '/plot?component=' + encodeURIComponent(comp)
            + '&sensor=' + encodeURIComponent(sens)
            + '&overlay=' + overlay;
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
  const comp = $('comp').value, sens = $('sens').value;
  if (!comp || !sens) return;
  const minSamples = prompt('Minimum samples to train (e.g. 30):', '30');
  if (minSamples === null) return;
  const historyDays = prompt('History days to use (blank = all):', '');
  if (historyDays === null) return;

  status('Training…', '', true);
  $('trainBtn').disabled = true;
  try {
    const body = new URLSearchParams({ component: comp, sensor: sens, min_samples: minSamples || '30' });
    if (historyDays) body.append('history_days', historyDays);
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


# ── components endpoint (needed by the new UI) ────────────────────────────────

@app.route("/api/components")
def api_components():
    if consolidated_df.empty:
        return jsonify([])
    return jsonify(sorted(consolidated_df["component_id"].dropna().unique().tolist()))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("\n  Dashboard → http://localhost:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
