"""
Package initialization for prognostics module.
"""
__version__ = "0.1.0"
__author__ = "Equipment Monitoring Team"

from .config import get_config, Config

__all__ = ['get_config', 'Config']
