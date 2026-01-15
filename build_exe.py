"""
NetMonitor Pro - Windows Executable Builder
Run this script on a Windows machine to create the .exe file
"""

import subprocess
import sys
import os
import shutil

def install_pyinstaller():
    """Install PyInstaller if not already installed"""
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_exe():
    """Build the executable using PyInstaller"""
    print("\n" + "="*50)
    print("NetMonitor Pro - Building Windows Executable")
    print("="*50 + "\n")
    
    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        install_pyinstaller()
    
    # Get the directory of this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define paths
    app_path = os.path.join(base_dir, "app.py")
    templates_path = os.path.join(base_dir, "templates")
    static_path = os.path.join(base_dir, "static")
    config_path = os.path.join(base_dir, "config.json")
    icon_path = os.path.join(base_dir, "icon.ico")  # Optional icon
    
    # PyInstaller arguments
    args = [
        app_path,
        "--name=NetMonitorPro",
        "--onefile",  # Single executable file
        "--console",  # Show console window (needed for server output)
        f"--add-data={templates_path}{os.pathsep}templates",
        f"--add-data={static_path}{os.pathsep}static",
        f"--add-data={config_path}{os.pathsep}.",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.http.h11_impl",
        "--hidden-import=uvicorn.protocols.http.httptools_impl",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.protocols.websockets.websockets_impl",
        "--hidden-import=uvicorn.protocols.websockets.wsproto_impl",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=uvicorn.lifespan.off",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.loops.asyncio",
        "--hidden-import=uvicorn.main",
        "--hidden-import=websockets",
        "--hidden-import=websockets.legacy",
        "--hidden-import=websockets.legacy.server",
        "--hidden-import=aiosqlite",
        "--hidden-import=apscheduler",
        "--hidden-import=apscheduler.schedulers.asyncio",
        "--hidden-import=apscheduler.triggers.interval",
        "--hidden-import=apscheduler.triggers.cron",
        "--hidden-import=jinja2",
        "--hidden-import=psutil",
        "--hidden-import=ping3",
        "--collect-all=uvicorn",
        "--collect-all=fastapi",
        "--collect-all=starlette",
        "--collect-submodules=uvicorn",
        "--noconfirm",  # Overwrite without asking
        "--clean",  # Clean cache before building
    ]
    
    # Add icon if it exists
    if os.path.exists(icon_path):
        args.append(f"--icon={icon_path}")
    
    print("Running PyInstaller with arguments:")
    print(" ".join(args[:5]) + " ...")
    print("\nThis may take a few minutes...\n")
    
    # Run PyInstaller
    subprocess.check_call([sys.executable, "-m", "PyInstaller"] + args)
    
    # Copy config.json to dist folder (so user can edit it)
    dist_dir = os.path.join(base_dir, "dist")
    if os.path.exists(dist_dir):
        shutil.copy2(config_path, dist_dir)
        print(f"\nCopied config.json to {dist_dir}")
    
    print("\n" + "="*50)
    print("BUILD COMPLETE!")
    print("="*50)
    print(f"\nExecutable location: {os.path.join(dist_dir, 'NetMonitorPro.exe')}")
    print("\nTo run:")
    print("1. Copy NetMonitorPro.exe and config.json to your desired location")
    print("2. Edit config.json to configure your targets and settings")
    print("3. Double-click NetMonitorPro.exe to start")
    print("4. Open http://localhost:8081 in your browser")
    print("\nNote: Keep config.json in the same folder as the .exe file")

if __name__ == "__main__":
    build_exe()
