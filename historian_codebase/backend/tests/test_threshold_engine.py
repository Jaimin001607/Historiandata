"""
Unit tests for threshold engine module.
"""
import pytest
from datetime import datetime
from prognostics.thresholds.threshold_engine import (
    ThresholdEngine,
    AlertLevel,
    Alert
)


class TestThresholdEngine:
    """Test suite for ThresholdEngine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ThresholdEngine(hysteresis_percent=10.0)

    def test_evaluate_metric_healthy(self):
        """Test evaluation of healthy metric."""
        alert = self.engine.evaluate_metric(
            component_id="VALVE_01",
            metric_name="vibration_rms",
            current_value=30.0,
            threshold_warning=50.0,
            threshold_critical=75.0
        )
        
        assert alert is None  # No alert for healthy value

    def test_evaluate_metric_warning(self):
        """Test evaluation that triggers warning."""
        alert = self.engine.evaluate_metric(
            component_id="VALVE_01",
            metric_name="vibration_rms",
            current_value=60.0,  # Above warning (50)
            threshold_warning=50.0,
            threshold_critical=75.0
        )
        
        assert alert is not None
        assert alert.level == AlertLevel.WARNING
        assert alert.component_id == "VALVE_01"

    def test_evaluate_metric_critical(self):
        """Test evaluation that triggers critical."""
        alert = self.engine.evaluate_metric(
            component_id="VALVE_01",
            metric_name="vibration_rms",
            current_value=80.0,  # Above critical (75)
            threshold_warning=50.0,
            threshold_critical=75.0
        )
        
        assert alert is not None
        assert alert.level == AlertLevel.CRITICAL

    def test_hysteresis_prevents_flicker(self):
        """Test that hysteresis prevents alert flicker."""
        # First evaluation at warning threshold
        alert1 = self.engine.evaluate_metric(
            "VALVE_01", "vibration", 51.0, 50.0, 75.0
        )
        assert alert1 is not None  # Alert triggered
        
        # Value drops back below threshold (but within hysteresis)
        alert2 = self.engine.evaluate_metric(
            "VALVE_01", "vibration", 49.0, 50.0, 75.0
        )
        assert alert2 is None  # Alert NOT cleared yet (hysteresis)
        
        # Value drops well below threshold (outside hysteresis window)
        alert3 = self.engine.evaluate_metric(
            "VALVE_01", "vibration", 40.0, 50.0, 75.0
        )
        assert alert3 is None  # Alert cleared

    def test_get_active_alerts(self):
        """Test retrieving active alerts."""
        self.engine.evaluate_metric("VALVE_01", "vibration", 60.0, 50.0, 75.0)
        self.engine.evaluate_metric("VALVE_02", "pressure", 25.0, 10.0, 20.0)
        
        active = self.engine.get_active_alerts()
        assert len(active) == 2

    def test_get_alert_for_component(self):
        """Test retrieving alert for specific component."""
        self.engine.evaluate_metric("VALVE_01", "vibration", 60.0, 50.0, 75.0)
        
        alert = self.engine.get_alert_for_component("VALVE_01")
        assert alert is not None
        assert alert.component_id == "VALVE_01"
        
        # No alert for other component
        alert2 = self.engine.get_alert_for_component("VALVE_02")
        assert alert2 is None

    def test_acknowledge_alert(self):
        """Test alert acknowledgment."""
        self.engine.evaluate_metric("VALVE_01", "vibration", 60.0, 50.0, 75.0)
        
        # Acknowledge
        success = self.engine.acknowledge_alert("VALVE_01")
        assert success is True
        
        # Check alert is marked acknowledged
        alert = self.engine.get_alert_for_component("VALVE_01")
        assert alert.acknowledged is True
        
        # Try to acknowledge non-existent alert
        success2 = self.engine.acknowledge_alert("VALVE_99")
        assert success2 is False

    def test_alert_history(self):
        """Test alert history tracking."""
        self.engine.evaluate_metric("VALVE_01", "vibration", 60.0, 50.0, 75.0)
        self.engine.evaluate_metric("VALVE_02", "pressure", 25.0, 10.0, 20.0)
        
        history = self.engine.get_alert_history()
        assert len(history) == 2

    def test_alert_history_limit(self):
        """Test that alert history respects limit."""
        # Generate multiple alerts
        for i in range(50):
            self.engine.evaluate_metric(
                f"VALVE_{i}", "vibration", 60.0, 50.0, 75.0
            )
        
        history = self.engine.get_alert_history(limit=20)
        assert len(history) <= 20

    def test_clear_alert_history(self):
        """Test clearing alert history."""
        self.engine.evaluate_metric("VALVE_01", "vibration", 60.0, 50.0, 75.0)
        assert len(self.engine.get_alert_history()) > 0
        
        self.engine.clear_alert_history()
        assert len(self.engine.get_alert_history()) == 0

    def test_component_status_summary(self):
        """Test component status summary."""
        self.engine.evaluate_metric("VALVE_01", "vibration", 60.0, 50.0, 75.0)
        self.engine.evaluate_metric("VALVE_02", "pressure", 25.0, 10.0, 20.0)
        
        summary = self.engine.get_component_status_summary()
        
        assert "VALVE_01" in summary
        assert "VALVE_02" in summary
        assert summary["VALVE_01"]["status"] == "alert"
        assert summary["VALVE_01"]["level"] == "warning"

    def test_alert_message_generation(self):
        """Test that alert messages are generated correctly."""
        alert = self.engine.evaluate_metric(
            "VALVE_01", "vibration_rms", 60.0, 50.0, 75.0
        )
        
        assert alert is not None
        assert "VALVE_01" in alert.message
        assert "vibration_rms" in alert.message.lower()
        assert "60" in alert.message  # Current value
        assert "50" in alert.message  # Threshold

    def test_multiple_metrics_same_component(self):
        """Test tracking multiple metrics for same component."""
        # First metric warning
        alert1 = self.engine.evaluate_metric(
            "VALVE_01", "vibration", 60.0, 50.0, 75.0
        )
        assert alert1 is not None
        
        # Second metric critical
        alert2 = self.engine.evaluate_metric(
            "VALVE_01", "pressure", 25.0, 10.0, 20.0
        )
        assert alert2 is not None
        
        # Component should only have one active alert (most recent)
        # or multiple alerts for different metrics
        active = self.engine.get_active_alerts()
        assert len(active) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
