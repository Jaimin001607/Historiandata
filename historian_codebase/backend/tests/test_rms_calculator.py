"""
Unit tests for RMS calculator module.
"""
import pytest
import math
from prognostics.metrics.rms_calculator import RMSCalculator


class TestRMSCalculator:
    """Test suite for RMSCalculator."""

    def test_calculate_rms_simple(self):
        """Test RMS calculation with simple signal."""
        # Signal: [3, 4] -> RMS = sqrt((9+16)/2) = sqrt(12.5) ≈ 3.536
        signal = [3, 4]
        rms = RMSCalculator.calculate_rms(signal)
        expected = math.sqrt((9 + 16) / 2)
        assert abs(rms - expected) < 0.001

    def test_calculate_rms_sine_wave(self):
        """Test RMS of sine wave (theoretical value = amplitude/sqrt(2))."""
        # 1 Hz sine wave with amplitude 10
        import numpy as np
        amplitude = 10
        t = np.linspace(0, 2 * np.pi, 1000)
        signal = amplitude * np.sin(t)
        
        rms = RMSCalculator.calculate_rms(signal)
        expected = amplitude / np.sqrt(2)
        
        # Allow 1% tolerance due to discretization
        assert abs(rms - expected) / expected < 0.01

    def test_calculate_rms_zeros(self):
        """Test RMS of all zeros."""
        signal = [0, 0, 0, 0]
        rms = RMSCalculator.calculate_rms(signal)
        assert rms == 0.0

    def test_calculate_rms_empty(self):
        """Test that empty signal raises ValueError."""
        with pytest.raises(ValueError):
            RMSCalculator.calculate_rms([])

    def test_calculate_rms_from_timeseries(self):
        """Test RMS calculation from timeseries data."""
        from datetime import datetime
        
        now = datetime.now()
        data = [
            (now, 3.0),
            (now, 4.0),
        ]
        
        rms = RMSCalculator.calculate_rms_from_timeseries(data)
        expected = math.sqrt((9 + 16) / 2)
        assert abs(rms - expected) < 0.001

    def test_windowed_rms(self):
        """Test sliding window RMS calculation."""
        signal = [1, 2, 3, 4, 5]
        window_size = 2
        
        rms_values = RMSCalculator.calculate_windowed_rms(signal, window_size)
        
        # Expected windows: [1,2], [2,3], [3,4], [4,5]
        expected = [
            math.sqrt((1 + 4) / 2),      # [1,2]
            math.sqrt((4 + 9) / 2),      # [2,3]
            math.sqrt((9 + 16) / 2),     # [3,4]
            math.sqrt((16 + 25) / 2),    # [4,5]
        ]
        
        assert len(rms_values) == len(expected)
        for calc, exp in zip(rms_values, expected):
            assert abs(calc - exp) < 0.001

    def test_windowed_rms_invalid_window(self):
        """Test that invalid window sizes raise error."""
        signal = [1, 2, 3, 4, 5]
        
        with pytest.raises(ValueError):
            RMSCalculator.calculate_windowed_rms(signal, 0)
        
        with pytest.raises(ValueError):
            RMSCalculator.calculate_windowed_rms(signal, 10)

    def test_remove_dc_offset(self):
        """Test DC offset removal."""
        signal = [5, 5, 5, 5]  # Mean = 5
        ac_signal = RMSCalculator.remove_dc_offset(signal)
        
        # All values should be near zero
        for val in ac_signal:
            assert abs(val) < 0.001

    def test_filter_outliers(self):
        """Test outlier filtering with 3-sigma rule."""
        import numpy as np
        signal = [1, 1, 1, 100, 1, 1, 1]  # 100 is outlier
        filtered = RMSCalculator.filter_outliers(signal)
        
        # Outlier should be NaN
        assert np.isnan(filtered[3])
        assert not np.isnan(filtered[0])

    def test_calculate_statistics(self):
        """Test comprehensive statistics calculation."""
        signal = [1, 2, 3, 4, 5]
        stats = RMSCalculator.calculate_statistics(signal)
        
        assert stats['mean'] == 3.0
        assert stats['min'] == 1.0
        assert stats['max'] == 5.0
        assert stats['sample_count'] == 5
        assert 'rms' in stats
        assert 'std' in stats
        assert 'peak' in stats

    def test_normalize_signal(self):
        """Test signal normalization to 0-1 range."""
        signal = [0, 10, 20]
        normalized = RMSCalculator.normalize_signal(signal)
        
        assert normalized[0] == 0.0
        assert normalized[1] == 0.5
        assert normalized[2] == 1.0

    def test_normalize_constant_signal(self):
        """Test normalization of constant signal."""
        signal = [5, 5, 5, 5]
        normalized = RMSCalculator.normalize_signal(signal)
        
        # All values should be 0 (no variance)
        for val in normalized:
            assert val == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
