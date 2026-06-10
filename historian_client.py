import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd


# Rows processed per chunk when reading large CSVs
_CHUNK_SIZE = 200_000


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

    def _normalize_chunk(self, chunk: pd.DataFrame, schema: str) -> pd.DataFrame:
        """Apply schema normalisation to a single chunk."""
        if 'record_timestamp' in chunk.columns:
            chunk = chunk.rename(columns={'record_timestamp': 'timestamp'})
        if 'power_plant_id' in chunk.columns:
            chunk = chunk.rename(columns={'power_plant_id': 'component_id'})

        if 'timestamp' not in chunk.columns or 'component_id' not in chunk.columns:
            return pd.DataFrame()

        if chunk['timestamp'].dtype == 'object':
            chunk['timestamp'] = (
                chunk['timestamp'].astype(str)
                .str.strip()
                .str.replace(r'\s+[A-Za-z]{2,5}$', '', regex=True)
            )

        chunk['timestamp'] = pd.to_datetime(chunk['timestamp'], errors='coerce', format='mixed', dayfirst=False)

        n_invalid = int(chunk['timestamp'].isna().sum())
        if n_invalid:
            self.logger.warning(f"{n_invalid} unparsable timestamps in chunk; dropped")

        chunk = chunk.dropna(subset=['timestamp', 'component_id'])
        return chunk

    def load_data(self, file_path: str) -> pd.DataFrame:
        """Load a historian CSV using chunked reading to handle large files."""
        schema = self.detect_schema(file_path)
        ts_col = 'record_timestamp' if schema == 'CSA' else 'timestamp'

        file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
        self.logger.info(f"Reading {Path(file_path).name} ({file_size_mb:.0f} MB)")

        chunks = []
        reader = pd.read_csv(
            file_path,
            chunksize=_CHUNK_SIZE,
            low_memory=False,
        )

        total_rows = 0
        for chunk in reader:
            normalised = self._normalize_chunk(chunk, schema)
            if not normalised.empty:
                chunks.append(normalised)
                total_rows += len(normalised)

        if not chunks:
            raise ValueError(f"No valid records loaded from {Path(file_path).name}")

        df = pd.concat(chunks, ignore_index=True)
        df = df.sort_values(by='timestamp').reset_index(drop=True)

        self.logger.info(f"Loaded {len(df)} records from {Path(file_path).name}")
        return df

    def _cache_path(self, file_path: str) -> Path:
        p = Path(file_path)
        return p.parent / (p.stem + '.parquet')

    def load_data_cached(self, file_path: str) -> pd.DataFrame:
        """Load a CSV, using a .parquet cache when available and up-to-date."""
        csv_path = Path(file_path)
        cache = self._cache_path(file_path)

        if cache.exists() and cache.stat().st_mtime >= csv_path.stat().st_mtime:
            self.logger.info(f"Loading from cache: {cache.name}")
            return pd.read_parquet(cache)

        df = self.load_data(file_path)

        try:
            df.to_parquet(cache, index=False)
            self.logger.info(f"Cached to {cache.name}")
        except Exception as exc:
            self.logger.warning(f"Could not write cache: {exc}")

        return df

    def merge_historical_files(self, file_paths: List[str], use_cache: bool = True) -> pd.DataFrame:
        """Load multiple historian files and consolidate them."""
        frames = []

        for file_path in file_paths:
            try:
                df = self.load_data_cached(file_path) if use_cache else self.load_data(file_path)
                frames.append(df)
            except Exception as exc:
                self.logger.warning(f"Skip {Path(file_path).name}: {exc}")

        if not frames:
            raise ValueError("No historian files could be loaded.")

        merged = pd.concat(frames, ignore_index=True)
        merged = merged.drop_duplicates(subset=['timestamp', 'component_id'], keep='first')
        merged = merged.sort_values(by=['component_id', 'timestamp']).reset_index(drop=True)

        self.logger.info(
            f"Consolidated {len(merged)} records from {len(frames)} files | "
            f"{merged['timestamp'].min().date()} → {merged['timestamp'].max().date()}"
        )
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
