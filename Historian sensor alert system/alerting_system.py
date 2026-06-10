import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class AlertingSystem:
    """Threshold-based alerting and event logging."""

    def __init__(self, log_file: str = "rms_alerts.log"):
        self.log_file = Path(log_file)
        self.events: List[Dict] = []
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(self.log_file)
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def process_detections(self, detection_results: List[Dict]) -> List[Dict]:
        alerts = []
        for result in detection_results:
            component_id = result.get('component_id')
            for alert in result.get('alerts', []):
                alert['timestamp'] = datetime.now().isoformat()
                alert['component_id'] = component_id
                alerts.append(alert)
                if alert['severity'] == 'CRITICAL':
                    self.logger.critical(alert['message'])
                else:
                    self.logger.warning(alert['message'])
        self.events.extend(alerts)
        return alerts

    def format_output(self, detection_results: List[Dict], alerts: List[Dict]) -> str:
        output = []
        output.append("=" * 90)
        output.append("RMS PROGNOSTICS ENGINE - SENSOR STATUS REPORT")
        output.append(f"Timestamp: {datetime.now().isoformat()}")
        output.append("=" * 90)

        for result in detection_results:
            output.append(f"\n[{result.get('component_id')}]")
            for sensor, stats in result.get('statistics', {}).items():
                output.append(f"\n  Sensor: {sensor}")
                output.append(f"    Anomalies: {stats['n_anomalies']}")
                output.append(f"    Mean Residual: {stats['mean_residual']:.6f}")
                output.append(f"    Std Residual: {stats['std_residual']:.6f}")
                output.append(f"    Max Z-Score: {stats['max_z_score']:.4f}")
                output.append(f"    CUSUM State: {stats['cusum_state']:.4f}")

        if alerts:
            output.append("\n" + "=" * 90)
            output.append("ALERT SUMMARY")
            output.append("=" * 90)
            for alert in alerts:
                output.append(f"[{alert.get('severity')}] {alert.get('component_id')} - {alert.get('sensor', 'N/A')}")
                output.append(f"  {alert.get('message')}")

        output.append("\n" + "=" * 90)
        return "\n".join(output)
