"""
RMS (Root Mean Square) calculation engine.
Core math for vibration and signal analysis.
"""
import numpy as np
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class RMSCalculator:
    """
    Calculates RMS (Root Mean Square) values from sensor signal data.
    
    RMS represents the magnitude of a varying signal:
    RMS = sqrt(mean(signal^2))
    """

    @staticmethod
    def calculate_rms(signal: List[float]) -> float:
        """
        Calculate RMS value from a signal array.
        
        Args:
            signal: List of signal values (samples)
            
        Returns:
            RMS value as float
            
        Raises:
            ValueError: If signal is empty
        """
        if not signal or len(signal) == 0:
            raise ValueError("Signal cannot be empty")
        
        signal_array = np.array(signal)
        rms = np.sqrt(np.mean(signal_array ** 2))
        return float(rms)

    @staticmethod
    def calculate_rms_from_timeseries(
        data: List[Tuple[float, float]]
    ) -> float:
        """
        Calculate RMS from time-series data (timestamp, value tuples).
        
        Args:
            data: List of (timestamp, value) tuples
            
        Returns:
            RMS value of the signal values
        """
        if not data:
            raise ValueError("Data cannot be empty")
        
        values = [v for _, v in data]
        return RMSCalculator.calculate_rms(values)

    @staticmethod
    def calculate_windowed_rms(
        signal: List[float],
        window_size: int
    ) -> List[float]:
        """
        Calculate RMS values in sliding windows.
        Useful for tracking RMS changes over time.
        
        Args:
            signal: List of signal values
            window_size: Size of sliding window
            
        Returns:
            List of RMS values, one per window
        """
        if window_size <= 0 or window_size > len(signal):
            raise ValueError("Invalid window size")
        
        rms_values = []
        for i in range(len(signal) - window_size + 1):
            window = signal[i:i + window_size]
            rms = RMSCalculator.calculate_rms(window)
            rms_values.append(rms)
        
        return rms_values

    @staticmethod
    def remove_dc_offset(signal: List[float]) -> List[float]:
        """
        Remove DC offset (mean value) from signal.
        Useful for AC-coupled sensor data.
        
        Args:
            signal: Original signal
            
        Returns:
            AC-coupled signal (DC offset removed)
        """
        signal_array = np.array(signal)
        mean = np.mean(signal_array)
        return (signal_array - mean).tolist()

    @staticmethod
    def filter_outliers(
        signal: List[float],
        std_dev_threshold: float = 3.0
    ) -> List[float]:
        """
        Remove outliers using standard deviation threshold.
        
        Args:
            signal: Original signal
            std_dev_threshold: Number of standard deviations (default 3-sigma)
            
        Returns:
            Filtered signal with outliers removed (set to NaN)
        """
        signal_array = np.array(signal)
        mean = np.mean(signal_array)
        std = np.std(signal_array)
        
        outlier_mask = np.abs(signal_array - mean) > std_dev_threshold * std
        filtered = signal_array.copy()
        filtered[outlier_mask] = np.nan
        
        return filtered.tolist()

    @staticmethod
    def calculate_statistics(signal: List[float]) -> dict:
        """
        Calculate comprehensive signal statistics.
        
        Args:
            signal: Signal values
            
        Returns:
            Dict with mean, std, min, max, rms, peak
        """
        signal_array = np.array(signal)
        return {
            'mean': float(np.mean(signal_array)),
            'std': float(np.std(signal_array)),
            'min': float(np.min(signal_array)),
            'max': float(np.max(signal_array)),
            'rms': float(RMSCalculator.calculate_rms(signal)),
            'peak': float(np.max(np.abs(signal_array))),
            'sample_count': len(signal)
        }

    @staticmethod
    def normalize_signal(signal: List[float]) -> List[float]:
        """
        Normalize signal to 0-1 range.
        
        Args:
            signal: Original signal
            
        Returns:
            Normalized signal
        """
        signal_array = np.array(signal)
        min_val = np.min(signal_array)
        max_val = np.max(signal_array)
        
        if max_val == min_val:
            return [0.0] * len(signal)
        
        normalized = (signal_array - min_val) / (max_val - min_val)
        return normalized.tolist()
