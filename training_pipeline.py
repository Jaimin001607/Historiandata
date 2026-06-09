import json
import logging
import pickle
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional

from historian_client import HistorianClient
from sensor_prognostic_model import SensorPrognosticModel
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


class RMSTrainingPipeline:
    """Training pipeline for historian datasets and per-sensor model generation."""

    def __init__(self, output_dir: str = "trained_models"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.client = HistorianClient(self.logger)
        self.models: Dict[str, SensorPrognosticModel] = {}
        self.training_stats: Dict = {}

    def load_and_consolidate(self, csv_files: List[str]) -> 'pd.DataFrame':
        consolidated = self.client.merge_historical_files(csv_files)
        self.training_stats['total_records'] = len(consolidated)
        self.training_stats['unique_components'] = consolidated['component_id'].nunique()
        self.training_stats['time_range'] = (
            consolidated['timestamp'].min().isoformat(),
            consolidated['timestamp'].max().isoformat(),
        )
        self.logger.info(
            f"Consolidated {len(consolidated)} records from "
            f"{self.training_stats['unique_components']} components"
        )
        return consolidated

    def _apply_history_window(self, df: 'pd.DataFrame', history_days: Optional[int]) -> 'pd.DataFrame':
        """Return a filtered DataFrame including only the last `history_days` days if provided."""
        if history_days is None:
            return df
        cutoff = datetime.now() - timedelta(days=history_days)
        return df[df['timestamp'] >= cutoff]

    def export_sensor_training_files(self, consolidated_data: 'pd.DataFrame', output_dir: Optional[str] = None) -> List[str]:
        export_path = Path(output_dir or "sensor_training_data")
        export_path.mkdir(parents=True, exist_ok=True)
        sensor_cols = self.client.get_sensor_columns(consolidated_data)
        saved_files: List[str] = []

        for component_id in consolidated_data['component_id'].unique():
            component_df = consolidated_data[consolidated_data['component_id'] == component_id]
            for sensor in sensor_cols:
                if sensor not in component_df.columns:
                    continue
                sensor_df = component_df[['timestamp', 'component_id', sensor]].dropna(subset=[sensor])
                if sensor_df.empty:
                    continue
                file_name = f"{component_id}_{sensor}_training.csv".replace(' ', '_')
                path = export_path / file_name
                sensor_df.to_csv(path, index=False)
                saved_files.append(str(path))
                self.logger.info(f"Exported training file: {path}")

        return saved_files

    def train_models_by_file(self, csv_files: List[str], min_samples: int = 30, history_days: Optional[int] = None) -> Dict[str, SensorPrognosticModel]:
        for file_path in csv_files:
            data = self.client.load_data(file_path)
            data = self._apply_history_window(data, history_days)
            file_tag = Path(file_path).stem.replace(' ', '_')
            for component_id in data['component_id'].unique():
                model_key = f"{file_tag}__{component_id}"
                model = SensorPrognosticModel(component_id, self.logger)
                try:
                    model.train(data, min_samples=min_samples)
                    self.models[model_key] = model
                    self.logger.info(f"Trained model {model_key}")
                except Exception as exc:
                    self.logger.warning(f"Could not train model {model_key}: {exc}")
        return self.models

    def train_sensor_models(self, consolidated_data: 'pd.DataFrame', min_samples: int = 30, history_days: Optional[int] = None) -> Dict[str, SensorPrognosticModel]:
        consolidated_data = self._apply_history_window(consolidated_data, history_days)
        sensor_cols = self.client.get_sensor_columns(consolidated_data)
        for component_id in consolidated_data['component_id'].unique():
            for sensor in sensor_cols:
                model_key = f"{component_id}__{sensor}"
                model = SensorPrognosticModel(component_id, self.logger)
                try:
                    model.train_sensor(sensor, consolidated_data, min_samples=min_samples)
                    self.models[model_key] = model
                    self.logger.info(f"Trained sensor model {model_key}")
                except Exception as exc:
                    self.logger.warning(f"Could not train sensor model {model_key}: {exc}")
        return self.models

    def plot_sensor(self, consolidated_data: 'pd.DataFrame', component_id: str, sensor: str,
                    start: Optional[datetime] = None, end: Optional[datetime] = None,
                    last_days: Optional[int] = None, show: bool = False,
                    overlay_baseline: bool = True) -> Optional[str]:
        """Plot time series for a sensor of a component. Returns saved file path or None on error."""
        df = consolidated_data[consolidated_data['component_id'] == component_id].copy()
        if df.empty:
            self.logger.warning(f"No data for component {component_id}")
            return None

        if sensor not in df.columns:
            self.logger.warning(f"Sensor {sensor} not found for {component_id}")
            return None

        if last_days is not None:
            cutoff = datetime.now() - timedelta(days=last_days)
            df = df[df['timestamp'] >= cutoff]

        if start is not None:
            df = df[df['timestamp'] >= start]
        if end is not None:
            df = df[df['timestamp'] <= end]

        if df.empty:
            self.logger.warning(f"No data in requested window for {component_id}:{sensor}")
            return None

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df['timestamp'], df[sensor].astype(float), marker='.', linestyle='-', label='value')
        # overlay baseline mean if available
        model_key = f"{component_id}__{sensor}"
        if overlay_baseline and model_key in self.models:
            model = self.models[model_key]
            if sensor in getattr(model, 'baseline_profiles', {}):
                mean = model.baseline_profiles[sensor].get('mean')
                if mean is not None:
                    ax.axhline(mean, color='red', linestyle='--', label='baseline mean')

        ax.set_title(f"{component_id} - {sensor}")
        ax.set_xlabel('Timestamp')
        ax.set_ylabel(sensor)
        ax.legend()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate()

        plots_dir = self.output_dir / 'plots'
        plots_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{component_id}_{sensor}_{int(datetime.now().timestamp())}.png".replace(' ', '_')
        path = plots_dir / file_name
        fig.savefig(path, bbox_inches='tight')
        if show:
            plt.show()
        plt.close(fig)
        self.logger.info(f"Saved plot {path}")
        return str(path)

    def save_models(self, save_dir: Optional[str] = None) -> str:
        save_path = Path(save_dir or self.output_dir)
        save_path.mkdir(exist_ok=True)

        for model_key, model in self.models.items():
            model_file = save_path / f"{model_key}.pkl"
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)
            self.logger.info(f"Saved model file {model_file}")

        metadata = {
            'timestamp': self.training_stats.get('timestamp', datetime.now().isoformat()) if 'timestamp' in self.training_stats else datetime.now().isoformat(),
            'n_models': len(self.models),
            'model_keys': list(self.models.keys()),
            'training_stats': self.training_stats,
        }
        metadata_file = save_path / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        return str(save_path)

    def load_models(self, load_dir: str) -> Dict[str, SensorPrognosticModel]:
        load_path = Path(load_dir)
        model_files = list(load_path.glob('*.pkl'))
        for model_file in model_files:
            with open(model_file, 'rb') as f:
                model = pickle.load(f)
                model_key = model_file.stem
                self.models[model_key] = model
                self.logger.info(f"Loaded model {model_key}")
        return self.models

    def get_model(self, model_key: str) -> Optional[SensorPrognosticModel]:
        return self.models.get(model_key)
