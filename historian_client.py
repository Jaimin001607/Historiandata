import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd


class HistorianClient:
    """Interface for historian data loading and preprocessing."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def detect_schema(self, file_path: str) -> str:
        """Detect known historian schema from CSV headers."""
        df0 = pd.read_csv(file_path, nrows=0)
        cols = set(df0.columns)

        if {'record_timestamp', 'power_plant_id'}.issubset(cols):
            return 'CSA'
        if {'timestamp', 'component_id'}.issubset(cols):
            return 'GENERIC'
        return 'UNKNOWN'

    def load_data(self, file_path: str) -> pd.DataFrame:
        """Load historian CSV data and normalize the schema."""
        schema = self.detect_schema(file_path)
        parse_dates = ['timestamp']

        if schema == 'CSA':
            parse_dates = ['record_timestamp']

        df = pd.read_csv(file_path, parse_dates=parse_dates)

        if 'record_timestamp' in df.columns:
            df = df.rename(columns={'record_timestamp': 'timestamp'})
        if 'power_plant_id' in df.columns:
            df = df.rename(columns={'power_plant_id': 'component_id'})

        if 'timestamp' not in df.columns or 'component_id' not in df.columns:
            msg = f"Unsupported historian schema in {Path(file_path).name}"
            self.logger.error(msg)
            raise ValueError(msg)

        # Ensure timestamp column is proper datetimes (coerce invalid formats)
        # Remove timezone strings (e.g., " EST") if present
        if df['timestamp'].dtype == 'object':
            df['timestamp'] = df['timestamp'].astype(str).str.replace(r'\s[A-Z]{3}$', '', regex=True)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        n_invalid = int(df['timestamp'].isna().sum())
        if n_invalid:
            self.logger.warning(
                f"{n_invalid} invalid or unparsable timestamps in {Path(file_path).name}; dropped"
            )

        df = df.dropna(subset=['timestamp', 'component_id'])
        df = df.sort_values(by='timestamp').reset_index(drop=True)

        self.logger.info(f"Loaded {len(df)} records from {Path(file_path).name}")
        return df

    def merge_historical_files(self, file_paths: List[str]) -> pd.DataFrame:
        """Load multiple historian files and consolidate them."""
        frames = []

        for file_path in file_paths:
            try:
                df = self.load_data(file_path)
                frames.append(df)
                self.logger.info(f"Loaded file: {Path(file_path).name}")
            except Exception as exc:
                self.logger.warning(f"Skip {Path(file_path).name}: {exc}")

        if not frames:
            raise ValueError("No historian files could be loaded.")

        merged = pd.concat(frames, ignore_index=True)
        merged = merged.drop_duplicates(subset=['timestamp', 'component_id'], keep='first')
        merged = merged.sort_values(by=['component_id', 'timestamp']).reset_index(drop=True)

        self.logger.info(f"Consolidated {len(merged)} records from {len(frames)} files")
        return merged

    def get_sensor_columns(self, df: pd.DataFrame) -> List[str]:
        """Return the numeric sensor columns for a historian dataset."""
        exclude = {'timestamp', 'component_id', 'power_plant_id', 'record_timestamp', 'state_label'}
        return [
            col for col in df.columns
            if col not in exclude and pd.api.types.is_numeric_dtype(df[col])
        ]

    def normalize_by_component(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize sensor values independently for each component."""
        df = df.copy()
        sensor_cols = self.get_sensor_columns(df)

        for component_id in df['component_id'].unique():
            mask = df['component_id'] == component_id
            component_df = df.loc[mask]

            for sensor_col in sensor_cols:
                if sensor_col not in component_df.columns:
                    continue

                subset = component_df[sensor_col].dropna()
                if len(subset) < 2:
                    df.loc[mask, f'{sensor_col}_normalized'] = np.nan
                    continue

                mean = subset.mean()
                std = subset.std()
                df.loc[mask, f'{sensor_col}_normalized'] = (subset - mean) / (std + 1e-6)

        return df
