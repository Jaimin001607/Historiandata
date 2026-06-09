"""
Configuration management for the prognostics system.
Loads settings from config.yaml and environment variables.
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import os


class Config:
    """Configuration handler for historian and monitoring settings."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config from YAML file or environment.
        
        Args:
            config_path: Path to config.yaml. Defaults to './config.yaml'
        """
        if config_path is None:
            config_path = os.getenv("PROGNOSTICS_CONFIG", "config.yaml")
        
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration file."""
        if not self.config_path.exists():
            return self._default_config()
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f) or {}

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration when config file doesn't exist."""
        return {
            "historian": {
                "type": "custom_database",
                "connection_string": os.getenv("HISTORIAN_CONNECTION_STRING", "")
            },
            "monitoring": {
                "interval_seconds": 60,
                "data_lookback_window": 300,
                "enabled": True
            },
            "alert": {
                "backend_url": os.getenv("ALERT_BACKEND_URL", "http://localhost:8000"),
                "enable_notifications": True
            },
            "components": {},
            "thresholds": {}
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def get_historian_config(self) -> Dict[str, Any]:
        """Get historian connection configuration."""
        return self.config.get('historian', {})

    def get_components(self) -> Dict[str, Any]:
        """Get monitored components configuration."""
        return self.config.get('components', {})

    def get_component_thresholds(self, component_id: str) -> Dict[str, Any]:
        """Get thresholds for a specific component."""
        components = self.get_components()
        return components.get(component_id, {}).get('metrics', {})

    def get_monitoring_interval(self) -> int:
        """Get monitoring interval in seconds."""
        return self.config.get('monitoring', {}).get('interval_seconds', 60)

    def get_lookback_window(self) -> int:
        """Get data lookback window in seconds."""
        return self.config.get('monitoring', {}).get('data_lookback_window', 300)

    def save_default_config(self):
        """Save default config to file for user customization."""
        with open(self.config_path, 'w') as f:
            yaml.dump(self._default_config(), f, default_flow_style=False)
        print(f"Default config saved to {self.config_path}")


# Global config instance
_config = None


def get_config(config_path: Optional[str] = None) -> Config:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
