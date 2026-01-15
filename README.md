# NetMonitor Pro

A modern, advanced network monitoring application inspired by MRTG, featuring real-time graphs, ping monitoring, bandwidth tracking, and comprehensive logging.

![NetMonitor Pro](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![License](https://img.shields.io/badge/license-MIT-purple.svg)

## Features

- 🎯 **Ping Monitoring** - Monitor multiple ISP IPs, DNS servers, and custom targets
- 📊 **Live Graphs** - Real-time visualization of latency and bandwidth
- 🌐 **Bandwidth Tracking** - Monitor upload/download speeds per gateway
- 📝 **Historical Logging** - SQLite database for persistent data storage
- ⚠️ **Alert System** - Configurable thresholds for latency and packet loss
- 🔄 **Real-time Updates** - WebSocket-based live dashboard
- 🎨 **Modern UI** - Beautiful, responsive dashboard with Tailwind CSS

## Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure your targets** (optional):
   Edit `config.json` to customize:
   - Ping targets (ISP IPs, DNS servers)
   - Gateway interfaces for bandwidth monitoring
   - Alert thresholds
   - Monitoring intervals

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open the dashboard:**
   Navigate to [http://localhost:8080](http://localhost:8080) in your browser.

## Configuration

The `config.json` file controls all monitoring settings:

```json
{
    "app_name": "NetMonitor Pro",
    "port": 8080,
    "ping_interval_seconds": 30,
    "bandwidth_interval_seconds": 5,
    "targets": [
        {
            "name": "Google DNS",
            "ip": "8.8.8.8",
            "type": "ping",
            "enabled": true
        }
    ],
    "gateways": [
        {
            "name": "Primary Gateway",
            "interface": "en0",
            "enabled": true
        }
    ],
    "alerts": {
        "enabled": true,
        "ping_threshold_ms": 100,
        "packet_loss_threshold_percent": 5
    }
}
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `ping_interval_seconds` | How often to ping targets | 30 |
| `bandwidth_interval_seconds` | How often to measure bandwidth | 5 |
| `data_retention_days` | Days to keep historical data | 30 |
| `alerts.ping_threshold_ms` | Alert when latency exceeds this | 100 |
| `alerts.packet_loss_threshold_percent` | Alert when packet loss exceeds this | 5 |

### Finding Network Interfaces

To find available network interfaces on your system:

**macOS/Linux:**
```bash
ifconfig | grep -E "^[a-z]"
# or
ip link show
```

**Windows:**
```cmd
ipconfig
```

Common interfaces:
- macOS: `en0` (WiFi), `en1` (Ethernet)
- Linux: `eth0`, `wlan0`, `ens33`
- Windows: `Ethernet`, `Wi-Fi`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/api/status` | GET | Current monitoring status |
| `/api/config` | GET | Current configuration |
| `/api/ping/history` | GET | Ping history data |
| `/api/bandwidth/history` | GET | Bandwidth history data |
| `/api/alerts` | GET | Recent alerts |
| `/api/statistics` | GET | Aggregated statistics |
| `/ws` | WebSocket | Real-time updates |

## Project Structure

```
netmonitor-pro/
├── app.py              # FastAPI application
├── monitor.py          # Network monitoring logic
├── database.py         # Database operations
├── config.json         # Configuration file
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Dashboard template
├── static/             # Static assets
└── README.md           # This file
```

## Troubleshooting

### Ping requires root/admin privileges
On some systems, raw ICMP packets require elevated privileges. The application uses the system `ping` command to avoid this issue.

### Interface not found
Run the application once to see available interfaces in the console output, then update `config.json` with the correct interface name.

### Port already in use
Change the `port` value in `config.json` to use a different port.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - feel free to use this project for personal or commercial purposes.

## Acknowledgments

- Inspired by [MRTG](https://oss.oetiker.ch/mrtg/)
- Built with [FastAPI](https://fastapi.tiangolo.com/)
- UI powered by [Tailwind CSS](https://tailwindcss.com/) and [Chart.js](https://www.chartjs.org/)
