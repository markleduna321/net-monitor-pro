<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# NetMonitor Pro - Development Instructions

This is a Python-based network monitoring application similar to MRTG but with advanced features.

## Project Overview
- **Backend**: FastAPI with WebSocket support for real-time updates
- **Frontend**: Modern responsive dashboard with Tailwind CSS and Chart.js
- **Database**: SQLite with async support (aiosqlite)
- **Scheduler**: APScheduler for periodic monitoring tasks

## Key Features
- Ping monitoring for multiple ISP IPs with latency tracking
- Bandwidth monitoring per gateway/interface
- Live graphs with real-time WebSocket updates
- Historical data logging with configurable retention
- Alert system with thresholds for latency and packet loss

## Main Components
- `app.py` - FastAPI application with WebSocket endpoint
- `monitor.py` - Network monitoring logic (ping, bandwidth)
- `database.py` - Database operations for storing metrics
- `config.json` - Configuration for targets, gateways, and alerts
- `templates/index.html` - Dashboard UI

## Running the Application
```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:8080 in your browser.

## Configuration
Edit `config.json` to:
- Add/remove ping targets (ISP IPs, DNS servers, etc.)
- Configure gateway interfaces for bandwidth monitoring
- Set monitoring intervals
- Configure alert thresholds
