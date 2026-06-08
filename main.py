import argparse
import time
import os
from pathlib import Path

import numpy as np
import pandas as pd


NUMERIC_COLS = ["temperature", "pressure", "flow_rate", "vibration"]


def generate_sample_data(output_dir="data"):
    Path(output_dir).mkdir(exist_ok=True)
    np.random.seed(42)

    n = 1000
    timestamps = pd.date_range("2024-01-01", periods=n, freq="1min")
    baseline = pd.DataFrame({
        "timestamp": timestamps,
        "temperature": np.random.normal(70.0, 2.0, n),
        "pressure":    np.random.normal(100.0, 5.0, n),
        "flow_rate":   np.random.normal(50.0, 3.0, n),
        "vibration":   np.random.normal(0.5, 0.1, n),
    })

    n_live = 200
    live_ts = pd.date_range("2024-02-01", periods=n_live, freq="1min")
    live = pd.DataFrame({
        "timestamp": live_ts,
        "temperature": np.random.normal(73.0, 2.5, n_live),   # drifted +3 °F
        "pressure":    np.random.normal(98.0, 5.0, n_live),   # drifted -2 psi
        "flow_rate":   np.random.normal(50.0, 3.0, n_live),   # nominal
        "vibration":   np.random.normal(0.85, 0.15, n_live),  # drifted high
    })

    b_path = os.path.join(output_dir, "baseline_profile.csv")
    l_path = os.path.join(output_dir, "live_stream.csv")
    baseline.to_csv(b_path, index=False)
    live.to_csv(l_path, index=False)
    return b_path, l_path


def profile(df):
    return df[NUMERIC_COLS].agg(["mean", "std", "min", "max"])


def drift_report(base_stats, live_stats, threshold=2.0):
    rows = []
    for col in NUMERIC_COLS:
        b_mean, b_std = base_stats.loc["mean", col], base_stats.loc["std", col]
        l_mean = live_stats.loc["mean", col]
        z = abs(l_mean - b_mean) / b_std if b_std else 0.0
        rows.append({
            "tag":           col,
            "baseline_mean": round(b_mean, 3),
            "live_mean":     round(l_mean, 3),
            "z_score":       round(z, 3),
            "status":        "DRIFT" if z > threshold else "OK",
        })
    return pd.DataFrame(rows)


def run_batch(baseline_path, live_path):
    base = pd.read_csv(baseline_path, parse_dates=["timestamp"])
    live = pd.read_csv(live_path,     parse_dates=["timestamp"])

    sep = "=" * 62
    print(f"\n{sep}")
    print("  HISTORIAN DATA — DRIFT ANALYSIS")
    print(sep)
    print(f"  Baseline : {baseline_path}  ({len(base)} rows)")
    print(f"  Live     : {live_path}  ({len(live)} rows)")
    print(f"  Tags     : {', '.join(NUMERIC_COLS)}")
    print(f"{sep}\n")

    b_stats = profile(base)
    l_stats = profile(live)

    print("BASELINE PROFILE:")
    print(b_stats.to_string(), "\n")
    print("LIVE STREAM PROFILE:")
    print(l_stats.to_string(), "\n")

    report = drift_report(b_stats, l_stats)
    print(f"{sep}")
    print("DRIFT REPORT  (threshold = 2.0 σ)")
    print(f"{sep}")
    print(report.to_string(index=False))

    drifted = report[report["status"] == "DRIFT"]
    print(f"\n  OK      : {len(report) - len(drifted)} tag(s)")
    print(f"  DRIFTED : {len(drifted)} tag(s)" +
          (f"  → {', '.join(drifted['tag'])}" if not drifted.empty else ""))
    print()


def run_stream(baseline_path, live_path, chunk_size=20, delay=0.4):
    base  = pd.read_csv(baseline_path, parse_dates=["timestamp"])
    live  = pd.read_csv(live_path,     parse_dates=["timestamp"])
    b_stats = profile(base)
    total   = len(live)

    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  STREAMING MODE  — chunk={chunk_size}, {total} live rows")
    print(f"{sep}")

    for start in range(0, total, chunk_size):
        chunk      = live.iloc[start:start + chunk_size]
        c_stats    = profile(chunk)
        report     = drift_report(b_stats, c_stats)
        drifted    = report[report["status"] == "DRIFT"]["tag"].tolist()
        rows_seen  = min(start + chunk_size, total)
        filled     = rows_seen * 30 // total
        bar        = "█" * filled + "░" * (30 - filled)
        flag       = "ALL OK" if not drifted else f"DRIFT → {', '.join(drifted)}"
        print(f"  [{bar}] {rows_seen:>4}/{total}  {flag}")
        time.sleep(delay)

    print(f"\n  Stream complete.\n")


def main():
    parser = argparse.ArgumentParser(description="Historian Data Drift Detector")
    parser.add_argument("--baseline", default=None, help="Baseline profile CSV")
    parser.add_argument("--live",     default=None, help="Live stream CSV")
    parser.add_argument("--stream",   action="store_true", help="Chunk-by-chunk streaming demo")
    args = parser.parse_args()

    baseline_path = args.baseline
    live_path     = args.live

    if baseline_path is None and live_path is None:
        print("No CSVs provided — generating sample data in data/ ...")
        baseline_path, live_path = generate_sample_data()
        print(f"  Saved: {baseline_path}\n  Saved: {live_path}")

    if args.stream:
        run_stream(baseline_path, live_path)
    else:
        run_batch(baseline_path, live_path)


if __name__ == "__main__":
    main()
