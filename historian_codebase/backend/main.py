#!/usr/bin/env python
"""
Main entry point for RMS Prognostics System API.

Usage:
    python main.py                    # Run API server
    python main.py --config config.yaml
    python main.py --port 8080
    python main.py --monitor-only     # Run monitoring without API
"""
import argparse
import logging
import sys
import asyncio

from prognostics.config import get_config
from prognostics.monitor import PrognosticsMonitor, MonitoringScheduler
from prognostics.api import create_app

import uvicorn


def setup_logging(level: str = "INFO"):
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('prognostics.log')
        ]
    )


async def run_monitor_only(config_path: str = None, interval: int = None):
    """Run monitoring without API server."""
    logger = logging.getLogger(__name__)
    logger.info("Starting monitoring engine (no API)")
    
    try:
        monitor = PrognosticsMonitor(config_path)
        
        if interval is None:
            interval = monitor.config.get_monitoring_interval()
        
        scheduler = MonitoringScheduler(monitor, interval)
        await scheduler.start()
    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
    except Exception as e:
        logger.error(f"Monitoring error: {e}")
        sys.exit(1)


def run_api_server(
    config_path: str = None,
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False
):
    """Run the FastAPI server."""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting API server on {host}:{port}")
    
    # Create FastAPI app
    app = create_app()
    
    # Run with uvicorn
    uvicorn.run(
        "prognostics.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RMS Prognostics System"
    )
    
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="API server host (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API server port (default: 8000)"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        help="Monitoring cycle interval in seconds"
    )
    
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    parser.add_argument(
        "--monitor-only",
        action="store_true",
        help="Run monitoring without API server"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes (dev mode)"
    )
    
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Initialize default config.yaml"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Initialize default config if requested
    if args.init_config:
        logger.info("Initializing default configuration...")
        config = get_config(args.config)
        config.save_default_config()
        logger.info("Configuration saved!")
        return 0
    
    # Run monitoring only (no API)
    if args.monitor_only:
        try:
            asyncio.run(run_monitor_only(args.config, args.interval))
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
            return 0
        except Exception as e:
            logger.error(f"Error: {e}")
            return 1
    
    # Run API server (with integrated monitoring)
    try:
        run_api_server(
            config_path=args.config,
            host=args.host,
            port=args.port,
            reload=args.reload
        )
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
