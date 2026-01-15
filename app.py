"""
NetMonitor Pro - Main Application
FastAPI-based web server with WebSocket support for real-time monitoring
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import List, Set, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from monitor import NetworkMonitor, PingResult, BandwidthMeasurement, format_bytes_rate
from database import (
    init_database, save_ping_result, save_bandwidth_measurement,
    save_alert, get_ping_history, get_bandwidth_history,
    get_alerts, acknowledge_alert, get_statistics, cleanup_old_data,
    get_ping_analytics, get_ping_logs_paginated
)


# Helper function to get base path (works for both script and PyInstaller exe)
def get_base_path():
    """Get the base path for resources - handles both dev and PyInstaller modes"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return sys._MEIPASS
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

def get_app_path():
    """Get the application directory (where config.json and db should be)"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - use exe directory
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))


BASE_PATH = get_base_path()
APP_PATH = get_app_path()


# Pydantic models for API
class TargetCreate(BaseModel):
    name: str
    ip: str
    enabled: bool = True

class TargetUpdate(BaseModel):
    name: Optional[str] = None
    ip: Optional[str] = None
    enabled: Optional[bool] = None


def save_config():
    """Save current config to file"""
    config_path = os.path.join(APP_PATH, 'config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)


# Load configuration
def load_config():
    config_path = os.path.join(APP_PATH, 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)


config = load_config()
DB_PATH = os.path.join(APP_PATH, config.get('database', 'netmonitor.db'))

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"Client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        print(f"Client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        # Remove disconnected clients
        self.active_connections -= disconnected


manager = ConnectionManager()
network_monitor: NetworkMonitor = None
scheduler: AsyncIOScheduler = None


async def ping_task():
    """Scheduled task to ping all targets"""
    global network_monitor
    if network_monitor is None:
        return
    
    results = await network_monitor.ping_all_targets()
    
    for result in results:
        # Save to database
        await save_ping_result(
            DB_PATH,
            result.target_name,
            result.target_ip,
            result.latency_ms,
            result.packet_loss,
            result.status
        )
        
        # Check for alerts
        alerts_config = config.get('alerts', {})
        if alerts_config.get('enabled', False):
            if result.latency_ms and result.latency_ms > alerts_config.get('ping_threshold_ms', 100):
                await save_alert(
                    DB_PATH,
                    'high_latency',
                    result.target_name,
                    f"High latency detected: {result.latency_ms:.1f}ms (threshold: {alerts_config['ping_threshold_ms']}ms)",
                    'warning'
                )
            
            if result.packet_loss > alerts_config.get('packet_loss_threshold_percent', 5):
                await save_alert(
                    DB_PATH,
                    'packet_loss',
                    result.target_name,
                    f"Packet loss detected: {result.packet_loss:.1f}% (threshold: {alerts_config['packet_loss_threshold_percent']}%)",
                    'critical' if result.packet_loss > 50 else 'warning'
                )
    
    # Broadcast to WebSocket clients
    await manager.broadcast({
        'type': 'ping_update',
        'data': [
            {
                'target_name': r.target_name,
                'target_ip': r.target_ip,
                'latency_ms': r.latency_ms,
                'packet_loss': r.packet_loss,
                'status': r.status,
                'timestamp': r.timestamp.isoformat()
            }
            for r in results
        ]
    })


async def bandwidth_task():
    """Scheduled task to measure bandwidth"""
    global network_monitor
    if network_monitor is None:
        return
    
    measurements = network_monitor.measure_all_bandwidth()
    
    for measurement in measurements:
        # Save to database
        await save_bandwidth_measurement(
            DB_PATH,
            measurement.gateway_name,
            measurement.interface,
            measurement.bytes_sent,
            measurement.bytes_recv,
            measurement.bytes_sent_rate,
            measurement.bytes_recv_rate
        )
    
    # Broadcast to WebSocket clients
    await manager.broadcast({
        'type': 'bandwidth_update',
        'data': [
            {
                'gateway_name': m.gateway_name,
                'interface': m.interface,
                'bytes_sent': m.bytes_sent,
                'bytes_recv': m.bytes_recv,
                'upload_rate': m.bytes_sent_rate,
                'download_rate': m.bytes_recv_rate,
                'upload_rate_formatted': format_bytes_rate(m.bytes_sent_rate),
                'download_rate_formatted': format_bytes_rate(m.bytes_recv_rate),
                'timestamp': m.timestamp.isoformat()
            }
            for m in measurements
        ]
    })


async def cleanup_task():
    """Scheduled task to clean up old data"""
    retention_days = config.get('data_retention_days', 30)
    await cleanup_old_data(DB_PATH, retention_days)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global network_monitor, scheduler
    
    # Initialize database
    await init_database(DB_PATH)
    
    # Initialize network monitor
    network_monitor = NetworkMonitor(config)
    
    # Initialize scheduler
    scheduler = AsyncIOScheduler()
    
    # Add scheduled jobs
    ping_interval = config.get('ping_interval_seconds', 30)
    bandwidth_interval = config.get('bandwidth_interval_seconds', 5)
    
    scheduler.add_job(ping_task, 'interval', seconds=ping_interval, id='ping_task')
    scheduler.add_job(bandwidth_task, 'interval', seconds=bandwidth_interval, id='bandwidth_task')
    scheduler.add_job(cleanup_task, 'cron', hour=3, minute=0, id='cleanup_task')  # Run at 3 AM
    
    scheduler.start()
    print(f"Scheduler started. Ping interval: {ping_interval}s, Bandwidth interval: {bandwidth_interval}s")
    
    # Run initial measurements
    await ping_task()
    await bandwidth_task()
    
    yield
    
    # Shutdown
    if scheduler:
        scheduler.shutdown()
    print("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="NetMonitor Pro",
    description="Advanced Network Monitoring System",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files (from BASE_PATH for bundled resources)
static_path = os.path.join(BASE_PATH, 'static')
os.makedirs(static_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Templates (from BASE_PATH for bundled resources)
templates_path = os.path.join(BASE_PATH, 'templates')
os.makedirs(templates_path, exist_ok=True)
templates = Jinja2Templates(directory=templates_path)


# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main dashboard"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "app_name": config.get('app_name', 'NetMonitor Pro'),
        "config": config
    })


@app.get("/api/status")
async def get_status():
    """Get current monitoring status"""
    if network_monitor is None:
        raise HTTPException(status_code=503, detail="Monitor not initialized")
    return network_monitor.get_current_status()


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return {
        "app_name": config.get('app_name'),
        "targets": config.get('targets', []),
        "gateways": config.get('gateways', []),
        "ping_interval": config.get('ping_interval_seconds'),
        "bandwidth_interval": config.get('bandwidth_interval_seconds')
    }


@app.get("/api/ping/history")
async def get_ping_history_api(target: str = None, hours: int = 24):
    """Get ping history"""
    history = await get_ping_history(DB_PATH, target, hours)
    return {"data": history}


@app.get("/api/bandwidth/history")
async def get_bandwidth_history_api(gateway: str = None, hours: int = 24):
    """Get bandwidth history"""
    history = await get_bandwidth_history(DB_PATH, gateway, hours)
    return {"data": history}


@app.get("/api/alerts")
async def get_alerts_api(unacknowledged: bool = False, hours: int = 24):
    """Get alerts"""
    alerts = await get_alerts(DB_PATH, unacknowledged, hours)
    return {"data": alerts}


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert_api(alert_id: int):
    """Acknowledge an alert"""
    await acknowledge_alert(DB_PATH, alert_id)
    return {"status": "acknowledged"}


@app.get("/api/statistics")
async def get_statistics_api(hours: int = 24):
    """Get aggregated statistics"""
    stats = await get_statistics(DB_PATH, hours)
    return stats


@app.get("/api/analytics/ping")
async def get_ping_analytics_api(target: str = None, hours: int = 24):
    """Get detailed ping analytics"""
    analytics = await get_ping_analytics(DB_PATH, target, hours)
    return analytics


@app.get("/api/logs/ping")
async def get_ping_logs_api(target: str = None, page: int = 1, 
                            per_page: int = 50, status: str = None):
    """Get paginated ping logs"""
    logs = await get_ping_logs_paginated(DB_PATH, target, page, per_page, status)
    return logs


@app.get("/api/interfaces")
async def get_interfaces():
    """Get available network interfaces"""
    if network_monitor is None:
        raise HTTPException(status_code=503, detail="Monitor not initialized")
    return {
        "interfaces": network_monitor.bandwidth_monitor.get_available_interfaces()
    }


# Target management endpoints
@app.get("/api/targets")
async def get_targets():
    """Get all ping targets"""
    return {"targets": config.get('targets', [])}


@app.post("/api/targets")
async def add_target(target: TargetCreate):
    """Add a new ping target"""
    global network_monitor
    
    # Check if target with same name or IP already exists
    existing_targets = config.get('targets', [])
    for t in existing_targets:
        if t['name'].lower() == target.name.lower():
            raise HTTPException(status_code=400, detail=f"Target with name '{target.name}' already exists")
        if t['ip'] == target.ip:
            raise HTTPException(status_code=400, detail=f"Target with IP '{target.ip}' already exists")
    
    new_target = {
        "name": target.name,
        "ip": target.ip,
        "type": "ping",
        "enabled": target.enabled
    }
    
    config['targets'].append(new_target)
    save_config()
    
    # Update the network monitor's config
    if network_monitor:
        network_monitor.config = config
    
    # Trigger an immediate ping of the new target
    await ping_task()
    
    return {"status": "created", "target": new_target}


@app.delete("/api/targets/{target_name}")
async def delete_target(target_name: str):
    """Delete a ping target"""
    global network_monitor
    
    targets = config.get('targets', [])
    original_length = len(targets)
    config['targets'] = [t for t in targets if t['name'].lower() != target_name.lower()]
    
    if len(config['targets']) == original_length:
        raise HTTPException(status_code=404, detail=f"Target '{target_name}' not found")
    
    save_config()
    
    # Update the network monitor's config
    if network_monitor:
        network_monitor.config = config
    
    return {"status": "deleted", "target_name": target_name}


@app.patch("/api/targets/{target_name}")
async def update_target(target_name: str, target_update: TargetUpdate):
    """Update a ping target (e.g., enable/disable)"""
    global network_monitor
    
    targets = config.get('targets', [])
    target_found = False
    
    for t in targets:
        if t['name'].lower() == target_name.lower():
            if target_update.name is not None:
                t['name'] = target_update.name
            if target_update.ip is not None:
                t['ip'] = target_update.ip
            if target_update.enabled is not None:
                t['enabled'] = target_update.enabled
            target_found = True
            updated_target = t
            break
    
    if not target_found:
        raise HTTPException(status_code=404, detail=f"Target '{target_name}' not found")
    
    save_config()
    
    # Update the network monitor's config
    if network_monitor:
        network_monitor.config = config
    
    return {"status": "updated", "target": updated_target}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        # Send current status on connect
        if network_monitor:
            await websocket.send_json({
                'type': 'initial_status',
                'data': network_monitor.get_current_status()
            })
        
        # Keep connection alive and listen for messages
        while True:
            data = await websocket.receive_text()
            
            # Handle client messages if needed
            try:
                message = json.loads(data)
                if message.get('type') == 'ping':
                    await websocket.send_json({'type': 'pong'})
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Manual trigger endpoints (for testing)
@app.post("/api/trigger/ping")
async def trigger_ping():
    """Manually trigger a ping check"""
    await ping_task()
    return {"status": "triggered"}


@app.post("/api/trigger/bandwidth")
async def trigger_bandwidth():
    """Manually trigger a bandwidth measurement"""
    await bandwidth_task()
    return {"status": "triggered"}


@app.post("/api/targets")
async def add_target(target: TargetCreate):
    """Add a new ping target"""
    config['targets'].append(target.dict())
    save_config()
    return {"status": "added"}


@app.delete("/api/targets/{target_name}")
async def delete_target(target_name: str):
    """Delete a ping target"""
    config['targets'] = [t for t in config['targets'] if t['name'] != target_name]
    save_config()
    return {"status": "deleted"}


@app.put("/api/targets/{target_name}")
async def update_target(target_name: str, target: TargetUpdate):
    """Update a ping target"""
    for t in config['targets']:
        if t['name'] == target_name:
            if target.name is not None:
                t['name'] = target.name
            if target.ip is not None:
                t['ip'] = target.ip
            if target.enabled is not None:
                t['enabled'] = target.enabled
            save_config()
            return {"status": "updated"}
    raise HTTPException(status_code=404, detail="Target not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=config.get('host', '0.0.0.0'),
        port=config.get('port', 8080),
        reload=True
    )
