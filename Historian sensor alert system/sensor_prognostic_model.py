import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class SensorPrognosticModel:
    """Prognostic model for sensor performance monitoring."""

    def __init__(self, component_id: str, logger: Optional[logging.Logger] = None):
        self.component_id = component_id
        self.logger = logger or logging.getLogger(__name__)

        self.baseline_profiles: Dict[str, Dict] = {}
        self.sensor_names: List[str] = []
        self.is_trained = False
        self.cusum_state: Dict[str, float] = {}

    def train(self, historical_data: pd.DataFrame, min_samples: int = 30) -> Tuple[Dict, Dict]:
        """Train baseline profiles for all sensors in a component dataset."""
        data = historical_data[historical_data['component_id'] == self.component_id].copy()
        if len(data) < min_samples:
            raise ValueError(
                f"Insufficient training records for {self.component_id}: {len(data)} < {min_samples}"
            )

        sensor_cols = [
            col for col in data.columns
            if col not in {'timestamp', 'component_id', 'record_timestamp', 'power_plant_id', 'state_label'}
            and pd.api.types.is_numeric_dtype(data[col])
        ]

        self.sensor_names = []
        stats = {}

        for sensor in sensor_cols:
            values = data[sensor].dropna()
            if len(values) < min_samples:
                continue

            profile = {
                'sensor': sensor,
                'mean': float(values.mean()),
                'std': float(values.std()),
                'median': float(values.median()),
                'q05': float(values.quantile(0.05)),
                'q25': float(values.quantile(0.25)),
                'q75': float(values.quantile(0.75)),
                'q95': float(values.quantile(0.95)),
                'min': float(values.min()),
                'max': float(values.max()),
                'n_samples': int(len(values)),
            }

            self.baseline_profiles[sensor] = profile
            self.cusum_state[sensor] = 0.0
            self.sensor_names.append(sensor)
            stats[sensor] = profile

        if not self.baseline_profiles:
            raise ValueError(f"No sensor profiles could be trained for {self.component_id}")

        self.is_trained = True
        self.logger.info(
            f"Trained {len(self.baseline_profiles)} sensor profiles for {self.component_id}"
        )
        return self.baseline_profiles, stats

    def train_sensor(self, sensor_name: str, historical_data: pd.DataFrame, min_samples: int = 30) -> Dict:
        """Train a baseline profile for a single sensor."""
        data = historical_data[historical_data['component_id'] == self.component_id].copy()
        if sensor_name not in data.columns:
            raise ValueError(f"Sensor '{sensor_name}' not found for {self.component_id}")

        values = data[sensor_name].dropna()
        if len(values) < min_samples:
            raise ValueError(
                f"Insufficient samples for sensor {sensor_name}: {len(values)} < {min_samples}"
            )

        profile = {
            'sensor': sensor_name,
            'mean': float(values.mean()),
            'std': float(values.std()),
            'median': float(values.median()),
            'q05': float(values.quantile(0.05)),
            'q25': float(values.quantile(0.25)),
            'q75': float(values.quantile(0.75)),
            'q95': float(values.quantile(0.95)),
            'min': float(values.min()),
            'max': float(values.max()),
            'n_samples': int(len(values)),
        }

        self.baseline_profiles = {sensor_name: profile}
        self.sensor_names = [sensor_name]
        self.cusum_state = {sensor_name: 0.0}
        self.is_trained = True

        self.logger.info(f"Trained single sensor profile for {self.component_id}:{sensor_name}")
        return profile

    def analyze(self, realtime_data: pd.DataFrame) -> pd.DataFrame:
        """Compare realtime sensor values against the fallback baseline."""
        if not self.is_trained:
            raise RuntimeError(f"Model not trained for {self.component_id}")

        results = realtime_data.copy()
        for sensor in self.sensor_names:
            if sensor not in results.columns:
                continue

            profile = self.baseline_profiles[sensor]
            expected = profile['mean']
            std = profile['std'] + 1e-6
            actual = results[sensor].astype(float).values
            residual = actual - expected
            results[f'{sensor}_residual'] = residual
            results[f'{sensor}_z_score'] = residual / std

        return results

    def detect_deviation(
        self,
        analyzed_data: pd.DataFrame,
        threshold_sigma: float = 2.5,
        use_cusum: bool = True,
        cusum_threshold: float = 5.0,
    ) -> Dict:
        """Detect anomalies and sustained drift per sensor."""
        if not self.is_trained:
            raise RuntimeError(f"Model not trained for {self.component_id}")

        results = {
            'component_id': self.component_id,
            'timestamp': datetime.now().isoformat(),
            'statistics': {},
            'sensor_anomalies': {},
            'alerts': [],
        }

        for sensor in self.sensor_names:
            z_score_col = f'{sensor}_z_score'
            residual_col = f'{sensor}_residual'
            if z_score_col not in analyzed_data.columns:
                continue

            z_scores = analyzed_data[z_score_col].dropna()
            if z_scores.empty:
                continue

            anomaly_mask = z_scores.abs() > threshold_sigma
            n_anomalies = int(anomaly_mask.sum())
            residuals = analyzed_data[residual_col].dropna().values

            if use_cusum and residuals.size:
                for residual in residuals:
                    self.cusum_state[sensor] = max(0, self.cusum_state[sensor] + residual - 0.5)

            stats = {
                'sensor': sensor,
                'n_anomalies': n_anomalies,
                'mean_residual': float(analyzed_data[residual_col].mean()),
                'std_residual': float(analyzed_data[residual_col].std()),
                'max_z_score': float(z_scores.abs().max()),
                'cusum_state': float(self.cusum_state[sensor]),
            }

            results['statistics'][sensor] = stats
            if n_anomalies:
                results['sensor_anomalies'][sensor] = {
                    'n_detected': n_anomalies,
                    'max_z_score': float(z_scores.abs().max()),
                    'last_timestamp': analyzed_data.loc[anomaly_mask, 'timestamp'].iloc[-1].isoformat(),
                }

        for sensor, data in results['sensor_anomalies'].items():
            results['alerts'].append(
                {
                    'severity': 'WARNING',
                    'sensor': sensor,
                    'message': (
                        f"Component {self.component_id} sensor {sensor}: "
                        f"{data['n_detected']} anomalies, max Z={data['max_z_score']:.2f}"
                    ),
                }
            )
            if results['statistics'][sensor]['cusum_state'] > cusum_threshold:
                results['alerts'].append(
                    {
                        'severity': 'CRITICAL',
                        'sensor': sensor,
                        'message': (
                            f"Component {self.component_id} sensor {sensor}: sustained drift detected "
                            f"(CUSUM={results['statistics'][sensor]['cusum_state']:.2f})"
                        ),
                    }
                )

        return results
