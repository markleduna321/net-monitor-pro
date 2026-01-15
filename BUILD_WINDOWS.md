# NetMonitor Pro - Windows Executable Build Guide

## Prerequisites

1. **Windows 10/11** (64-bit recommended)
2. **Python 3.9 or higher** - Download from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"

## Building the Executable

### Option 1: Easy Build (Recommended)

1. Double-click `build_windows.bat`
2. Wait for the build to complete (2-5 minutes)
3. Find your executable in the `dist` folder

### Option 2: Manual Build

1. Open Command Prompt or PowerShell in the project folder
2. Run the following commands:

```powershell
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build the executable
python build_exe.py
```

## After Building

Your `dist` folder will contain:
- `NetMonitorPro.exe` - The main application
- `config.json` - Configuration file

## Running the Application

1. Copy `NetMonitorPro.exe` and `config.json` to your desired location
2. Edit `config.json` to configure:
   - Your ping targets (ISP IPs, DNS servers, etc.)
   - Network interface name for bandwidth monitoring
   - Alert thresholds
3. Double-click `NetMonitorPro.exe` to start
4. Open your browser to `http://localhost:8081`

## Configuration for Windows

### Finding Your Network Interface Name

Run this in PowerShell:
```powershell
Get-NetAdapter | Select-Object Name, Status
```

Common interface names:
- `Ethernet` - Wired connection
- `Wi-Fi` - Wireless connection
- `Ethernet 2` - Secondary wired connection

Update `config.json`:
```json
"gateways": [
    {
        "name": "Primary Gateway",
        "interface": "Ethernet",
        "enabled": true
    }
]
```

## Firewall Settings

If ping monitoring doesn't work:
1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Add `NetMonitorPro.exe` and allow both Private and Public networks

## Troubleshooting

### "App won't start"
- Ensure `config.json` is in the same folder as the .exe
- Try running as Administrator

### "Port already in use"
- Change the port in `config.json`:
```json
"port": 8082
```

### "Can't ping targets"
- Run as Administrator
- Check Windows Firewall settings

### "Interface not found"
- Run `Get-NetAdapter` in PowerShell to find your interface name
- Update the interface name in `config.json`

## Database Location

The SQLite database (`netmonitor.db`) is created in the same folder as the executable.

## Support

For issues or feature requests, please check the main README.md or open an issue on GitHub.
