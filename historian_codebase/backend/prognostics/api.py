"""
FastAPI REST API for prognostics system.
Provides endpoints for monitoring and alert management.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
import asyncio

from .monitor import PrognosticsMonitor, MonitoringScheduler
from .config import get_config

logger = logging.getLogger(__name__)

# Pydantic models for API
class MetricValue(BaseModel):
    metric_name: str
    value: float
    unit: str
    status: str
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None


class HealthStatus(BaseModel):
    component_id: str
    overall_status: str
    metrics: Dict[str, MetricValue]
    timestamp: str
    alert_triggered: bool


class AlertResponse(BaseModel):
    component_id: str
    level: str
    metric: str
    value: float
    threshold: float
    message: str
    timestamp: str
    acknowledged: bool


class AcknowledgeRequest(BaseModel):
    component_id: str


# Global state
monitor: Optional[PrognosticsMonitor] = None
scheduler: Optional[MonitoringScheduler] = None
scheduler_task: Optional[asyncio.Task] = None


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title="RMS Prognostics API",
        description="Equipment health monitoring via RMS-based metrics",
        version="0.1.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize monitoring system on startup."""
        global monitor, scheduler, scheduler_task
        try:
            config = get_config()
            monitor = PrognosticsMonitor()
            
            interval = config.get_monitoring_interval()
            scheduler = MonitoringScheduler(monitor, interval)
            
            # Start scheduler in background
            scheduler_task = asyncio.create_task(scheduler.start())
            logger.info("API startup complete")
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            raise
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        global scheduler, scheduler_task
        if scheduler:
            scheduler.stop()
        if scheduler_task:
            scheduler_task.cancel()
        logger.info("API shutdown complete")
    
    # ============ Health Endpoints ============
    
    @app.get("/health")
    async def health_check():
        """System health check endpoint."""
        if not monitor:
            raise HTTPException(status_code=503, detail="Monitor not initialized")
        
        historian_ok = monitor.historian.health_check() if monitor.historian else False
        
        return {
            "status": "healthy" if historian_ok else "degraded",
            "monitor_running": monitor.is_running,
            "historian_connected": historian_ok,
            "timestamp": datetime.now().isoformat()
        }
    
    @app.get("/components")
    async def list_components():
        """Get list of monitored components."""
        if not monitor:
            raise HTTPException(status_code=503, detail="Monitor not initialized")
        
        components = monitor.config.get_components()
        return {
            "components": list(components.keys()),
            "total": len(components),
            "timestamp": datetime.now().isoformat()
        }
    
    @app.get("/component/{component_id}/health")
    async def get_component_health(component_id: str):
        """Get health status for a specific component."""
        if not monitor:
            raise HTTPException(status_code=503, detail="Monitor not initialized")
        
        health = monitor.get_current_health(component_id)
        if not health:
            raise HTTPException(status_code=404, detail=f"Component {component_id} not found")
        
        return health
    
    # ============ Alert Endpoints ============
    
    @app.get("/alerts")
    async def get_alerts():
        """Get all active alerts."""
        if not monitor:
            raise HTTPException(status_code=503, detail="Monitor not initialized")
        
        alerts = monitor.get_all_alerts()
        return {
            "alerts": alerts,
            "total": len(alerts),
            "timestamp": datetime.now().isoformat()
        }
    
    @app.get("/alerts/history")
    async def get_alert_history(limit: int = 100):
        """Get alert history."""
        if not monitor:
            raise HTTPException(status_code=503, detail="Monitor not initialized")
        
        history = monitor.threshold_engine.get_alert_history(limit)
        return {
            "alerts": [
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
                for a in history
            ],
            "total": len(history),
            "timestamp": datetime.now().isoformat()
        }
    
    @app.post("/alerts/{component_id}/acknowledge")
    async def acknowledge_alert(component_id: str):
        """Acknowledge an alert for a component."""
        if not monitor:
            raise HTTPException(status_code=503, detail="Monitor not initialized")
        
        success = monitor.acknowledge_alert(component_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"No active alert for {component_id}")
        
        return {
            "component_id": component_id,
            "acknowledged": True,
            "timestamp": datetime.now().isoformat()
        }
    
    # ============ Control Endpoints ============
    
    @app.post("/monitor/start")
    async def start_monitor():
        """Start the monitoring system."""
        if not monitor:
            raise HTTPException(status_code=503, detail="Monitor not initialized")
        
        monitor.start()
        return {"status": "started", "timestamp": datetime.now().isoformat()}
    
    @app.post("/monitor/stop")
    async def stop_monitor():
        """Stop the monitoring system."""
        if not monitor:
            raise HTTPException(status_code=503, detail="Monitor not initialized")
        
        monitor.stop()
        return {"status": "stopped", "timestamp": datetime.now().isoformat()}
    
    @app.get("/monitor/status")
    async def monitor_status():
        """Get monitoring system status."""
        if not monitor:
            raise HTTPException(status_code=503, detail="Monitor not initialized")
        
        return {
            "running": monitor.is_running,
            "interval_seconds": monitor.config.get_monitoring_interval(),
            "active_components": len(monitor.config.get_components()),
            "active_alerts": len(monitor.get_all_alerts()),
            "timestamp": datetime.now().isoformat()
        }
    
    return app


# Create the application
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
