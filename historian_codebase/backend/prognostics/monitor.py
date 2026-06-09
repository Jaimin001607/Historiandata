"""
Main monitoring loop for prognostics system.
Orchestrates data sampling, metric calculation, threshold evaluation, and alerting.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import asyncio

from .config import get_config
from .historian_connector import HistorianConnector
from .metrics.health_engine import HealthEngine, HealthStatus
from .thresholds.threshold_engine import ThresholdEngine, Alert

logger = logging.getLogger(__name__)


class PrognosticsMonitor:
    """
    Main monitoring engine that orchestrates the prognostics system.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the monitoring system.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = get_config(config_path)
        self.historian = None
        self.health_engine = HealthEngine()
        self.threshold_engine = ThresholdEngine(hysteresis_percent=10.0)
        self.is_running = False
        self.last_sample_time: Dict[str, datetime] = {}
        self._initialize_historian()

    def _initialize_historian(self):
        """Initialize historian connection."""
        try:
            historian_config = self.config.get_historian_config()
            conn_string = historian_config.get('connection_string', '')
            self.historian = HistorianConnector(conn_string)
            logger.info("Historian connector initialized")
        except Exception as e:
            logger.error(f"Failed to initialize historian: {e}")
            raise

    def start(self):
        """Start the monitoring system."""
        if self.is_running:
            logger.warning("Monitor already running")
            return
        
        self.is_running = True
        logger.info("Prognostics monitor started")

    def stop(self):
        """Stop the monitoring system."""
        self.is_running = False
        if self.historian:
            self.historian.close()
        logger.info("Prognostics monitor stopped")

    def run_cycle(self) -> List[Alert]:
        """
        Execute one monitoring cycle:
        1. Sample data from historian
        2. Calculate health metrics
        3. Evaluate thresholds
        4. Generate alerts
        
        Returns:
            List of alerts generated in this cycle
        """
        if not self.is_running:
            logger.debug("Monitor not running, skipping cycle")
            return []
        
        alerts = []
        components = self.config.get_components()
        
        for component_id, component_config in components.items():
            try:
                # Sample sensor data for this component
                sensor_data = self._sample_component_data(component_id, component_config)
                
                if not sensor_data:
                    logger.debug(f"No sensor data for {component_id}")
                    continue
                
                # Calculate health metrics
                thresholds = component_config.get('metrics', {})
                health = self.health_engine.calculate_health_metrics(
                    component_id,
                    sensor_data,
                    thresholds
                )
                
                # Evaluate thresholds and generate alerts
                component_alerts = self._evaluate_component_health(
                    component_id,
                    health,
                    thresholds
                )
                alerts.extend(component_alerts)
                
                # Track trends
                trends = self.health_engine.track_health_trend(component_id, health)
                logger.debug(f"{component_id} trends: {trends}")
                
            except Exception as e:
                logger.error(f"Error monitoring {component_id}: {e}")
                continue
        
        return alerts

    def _sample_component_data(
        self,
        component_id: str,
        component_config: Dict
    ) -> Optional[Dict[str, List]]:
        """
        Sample sensor data for a component.
        
        Args:
            component_id: Component identifier
            component_config: Component configuration with metric/tag mappings
            
        Returns:
            Dict of {metric_name: [(timestamp, value), ...]} or None if no data
        """
        if not self.historian:
            return None
        
        metrics = component_config.get('metrics', {})
        sensor_data = {}
        
        # Get lookback window from config
        lookback_seconds = self.config.get_lookback_window()
        end_time = datetime.now()
        start_time = end_time - timedelta(seconds=lookback_seconds)
        
        for metric_name, metric_config in metrics.items():
            tag_name = metric_config.get('tag_name')
            if not tag_name:
                logger.warning(f"No tag_name for {component_id}.{metric_name}")
                continue
            
            try:
                data = self.historian.get_tag_data(tag_name, start_time, end_time)
                if data:
                    sensor_data[metric_name] = data
                    logger.debug(f"Sampled {len(data)} points for {tag_name}")
            except Exception as e:
                logger.error(f"Error sampling {tag_name}: {e}")
        
        return sensor_data if sensor_data else None

    def _evaluate_component_health(
        self,
        component_id: str,
        health,
        thresholds: Dict
    ) -> List[Alert]:
        """
        Evaluate component health and generate alerts.
        
        Args:
            component_id: Component identifier
            health: ComponentHealth object
            thresholds: Metric thresholds
            
        Returns:
            List of alerts generated
        """
        alerts = []
        
        for metric_name, metric in health.metrics.items():
            metric_thresholds = thresholds.get(metric_name, {})
            
            alert = self.threshold_engine.evaluate_metric(
                component_id=component_id,
                metric_name=metric_name,
                current_value=metric.value,
                threshold_warning=metric_thresholds.get('warning'),
                threshold_critical=metric_thresholds.get('critical')
            )
            
            if alert:
                alerts.append(alert)
        
        return alerts

    def get_current_health(self, component_id: str) -> Optional[Dict]:
        """Get current health status of a component."""
        components = self.config.get_components()
        if component_id not in components:
            return None
        
        # Would return cached health from last cycle
        return {"component_id": component_id, "status": "unknown"}

    def get_all_alerts(self) -> List[Dict]:
        """Get all active alerts."""
        alerts = self.threshold_engine.get_active_alerts()
        return [
            {
                "component_id": a.component_id,
                "level": a.level.value,
                "metric": a.metric_name,
                "value": a.current_value,
                "threshold": a.threshold_value,
                "message": a.message,
                "timestamp": a.timestamp.isoformat(),
                "acknowledged": a.acknowledged
            }
            for a in alerts
        ]

    def acknowledge_alert(self, component_id: str) -> bool:
        """Acknowledge an alert."""
        return self.threshold_engine.acknowledge_alert(component_id)


class MonitoringScheduler:
    """
    Scheduler for running monitoring cycles at regular intervals.
    """

    def __init__(self, monitor: PrognosticsMonitor, interval_seconds: int = 60):
        """
        Initialize scheduler.
        
        Args:
            monitor: PrognosticsMonitor instance
            interval_seconds: Interval between monitoring cycles
        """
        self.monitor = monitor
        self.interval_seconds = interval_seconds
        self.is_running = False

    async def start(self):
        """Start the monitoring scheduler."""
        self.is_running = True
        self.monitor.start()
        logger.info(f"Monitoring scheduler started (interval: {self.interval_seconds}s)")
        
        try:
            while self.is_running:
                try:
                    alerts = self.monitor.run_cycle()
                    if alerts:
                        logger.info(f"Generated {len(alerts)} alerts in this cycle")
                except Exception as e:
                    logger.error(f"Error in monitoring cycle: {e}")
                
                # Wait before next cycle
                await asyncio.sleep(self.interval_seconds)
        except asyncio.CancelledError:
            logger.info("Monitoring scheduler cancelled")
            self.stop()
        except Exception as e:
            logger.error(f"Monitoring scheduler error: {e}")
            self.stop()

    def stop(self):
        """Stop the monitoring scheduler."""
        self.is_running = False
        self.monitor.stop()
        logger.info("Monitoring scheduler stopped")
