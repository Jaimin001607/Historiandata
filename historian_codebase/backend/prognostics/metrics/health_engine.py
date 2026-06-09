"""
Health metrics engine.
Aggregates RMS calculations and other metrics into component health status.
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging

from .rms_calculator import RMSCalculator

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """Single health metric measurement."""
    metric_name: str
    value: float
    unit: str
    status: HealthStatus
    timestamp: datetime
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None


@dataclass
class ComponentHealth:
    """Overall health status of a component."""
    component_id: str
    overall_status: HealthStatus
    metrics: Dict[str, HealthMetric]
    timestamp: datetime
    alert_triggered: bool = False
    alert_message: Optional[str] = None


class HealthEngine:
    """
    Aggregates metrics and determines component health status.
    """

    def __init__(self):
        """Initialize health engine."""
        self.rms_calc = RMSCalculator()
        self.health_history: Dict[str, List[ComponentHealth]] = {}

    def calculate_health_metrics(
        self,
        component_id: str,
        sensor_data: Dict[str, List[Tuple[datetime, float]]],
        thresholds: Dict[str, Dict[str, float]]
    ) -> ComponentHealth:
        """
        Calculate comprehensive health metrics for a component.
        
        Args:
            component_id: Component identifier
            sensor_data: Dict of {metric_name: [(timestamp, value), ...]}
            thresholds: Dict of {metric_name: {warning: X, critical: Y}}
            
        Returns:
            ComponentHealth object with all metrics and overall status
        """
        metrics = {}
        worst_status = HealthStatus.HEALTHY
        
        for metric_name, data_points in sensor_data.items():
            if not data_points:
                continue
            
            # Calculate RMS for this metric
            metric_value = RMSCalculator.calculate_rms_from_timeseries(data_points)
            metric_thresholds = thresholds.get(metric_name, {})
            
            # Determine status based on thresholds
            status = self._determine_status(
                metric_value,
                metric_thresholds.get('warning'),
                metric_thresholds.get('critical')
            )
            
            # Update worst status
            if self._status_is_worse(status, worst_status):
                worst_status = status
            
            # Create metric entry
            metrics[metric_name] = HealthMetric(
                metric_name=metric_name,
                value=metric_value,
                unit=metric_thresholds.get('unit', 'unknown'),
                status=status,
                timestamp=datetime.now(),
                threshold_warning=metric_thresholds.get('warning'),
                threshold_critical=metric_thresholds.get('critical')
            )
        
        # Determine if alert should trigger
        alert_triggered = worst_status in [HealthStatus.WARNING, HealthStatus.CRITICAL]
        alert_message = self._generate_alert_message(component_id, metrics, worst_status) if alert_triggered else None
        
        return ComponentHealth(
            component_id=component_id,
            overall_status=worst_status,
            metrics=metrics,
            timestamp=datetime.now(),
            alert_triggered=alert_triggered,
            alert_message=alert_message
        )

    def _determine_status(
        self,
        value: float,
        threshold_warning: Optional[float],
        threshold_critical: Optional[float]
    ) -> HealthStatus:
        """
        Determine health status based on thresholds.
        
        Args:
            value: Current metric value
            threshold_warning: Warning threshold (above = warning)
            threshold_critical: Critical threshold (above = critical)
            
        Returns:
            HealthStatus enumeration
        """
        if threshold_critical is not None and value >= threshold_critical:
            return HealthStatus.CRITICAL
        if threshold_warning is not None and value >= threshold_warning:
            return HealthStatus.WARNING
        return HealthStatus.HEALTHY

    def _status_is_worse(self, status1: HealthStatus, status2: HealthStatus) -> bool:
        """Check if status1 is worse than status2."""
        severity = {
            HealthStatus.CRITICAL: 3,
            HealthStatus.WARNING: 2,
            HealthStatus.HEALTHY: 1,
            HealthStatus.UNKNOWN: 0
        }
        return severity.get(status1, 0) > severity.get(status2, 0)

    def _generate_alert_message(
        self,
        component_id: str,
        metrics: Dict[str, HealthMetric],
        overall_status: HealthStatus
    ) -> str:
        """
        Generate alert message describing health issue.
        
        Args:
            component_id: Component identifier
            metrics: Dict of metrics
            overall_status: Overall health status
            
        Returns:
            Alert message string
        """
        critical_metrics = [m for m in metrics.values() if m.status == HealthStatus.CRITICAL]
        warning_metrics = [m for m in metrics.values() if m.status == HealthStatus.WARNING]
        
        parts = [f"{component_id} health status: {overall_status.value.upper()}"]
        
        if critical_metrics:
            parts.append(f"CRITICAL: {', '.join([f'{m.metric_name}={m.value:.2f}{m.unit}' for m in critical_metrics])}")
        
        if warning_metrics:
            parts.append(f"WARNING: {', '.join([f'{m.metric_name}={m.value:.2f}{m.unit}' for m in warning_metrics])}")
        
        return " | ".join(parts)

    def track_health_trend(
        self,
        component_id: str,
        health_record: ComponentHealth,
        lookback_count: int = 10
    ) -> Dict[str, float]:
        """
        Track health metric trends over time.
        
        Args:
            component_id: Component identifier
            health_record: Current health measurement
            lookback_count: How many historical records to analyze
            
        Returns:
            Dict with trend metrics (rate_of_change, degradation_rate, etc.)
        """
        if component_id not in self.health_history:
            self.health_history[component_id] = []
        
        self.health_history[component_id].append(health_record)
        
        # Keep only recent history
        if len(self.health_history[component_id]) > lookback_count:
            self.health_history[component_id] = self.health_history[component_id][-lookback_count:]
        
        history = self.health_history[component_id]
        if len(history) < 2:
            return {}
        
        trends = {}
        for metric_name in health_record.metrics:
            values = [h.metrics[metric_name].value for h in history if metric_name in h.metrics]
            if len(values) >= 2:
                rate_of_change = (values[-1] - values[0]) / (len(values) - 1)
                trends[f"{metric_name}_roc"] = rate_of_change
        
        return trends

    def predict_failure_time(
        self,
        component_id: str,
        metric_name: str,
        critical_threshold: float
    ) -> Optional[float]:
        """
        Estimate time to critical failure based on current trend.
        Simple linear extrapolation.
        
        Args:
            component_id: Component identifier
            metric_name: Metric to analyze
            critical_threshold: Failure threshold value
            
        Returns:
            Estimated minutes until failure, or None if not degrading
        """
        history = self.health_history.get(component_id, [])
        if len(history) < 2:
            return None
        
        values = [h.metrics.get(metric_name).value for h in history if metric_name in h.metrics]
        if len(values) < 2:
            return None
        
        current = values[-1]
        if current >= critical_threshold:
            return 0.0
        
        # Calculate rate of change
        roc = (values[-1] - values[-2]) / len(values)
        if roc <= 0:
            return None  # Not degrading
        
        # Estimate minutes to failure (assuming 1-minute sampling)
        minutes_remaining = (critical_threshold - current) / roc
        return max(0, minutes_remaining)
