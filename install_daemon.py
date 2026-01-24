#!/usr/bin/env python3
"""
Post-installation script to set up persistent daemon
Installs platform-specific service to run at system startup
"""

import os
import sys
import platform
from pathlib import Path
import subprocess


def install_macos():
    """Install as macOS launchd service"""
    plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.local.agent-rules-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>agent_rules_sync</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_dir}/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{log_dir}/stderr.log</string>
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>"""

    python_path = sys.executable
    log_dir = str(Path.home() / ".config" / "agent-rules-sync")

    # Create log directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.local.agent-rules-sync.plist"
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    plist_content = plist_content.format(python_path=python_path, log_dir=log_dir)

    with open(plist_path, 'w') as f:
        f.write(plist_content)

    # Set permissions
    os.chmod(plist_path, 0o644)

    # Load the service
    try:
        subprocess.run(['launchctl', 'load', str(plist_path)], check=True,
                       capture_output=True)
        print(f"✓ macOS daemon installed and started")
        print(f"  Service: com.local.agent-rules-sync")
        print(f"  Plist: {plist_path}")
        print(f"  Logs: {log_dir}/stdout.log and stderr.log")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Could not load launchd service: {e}")
        print(f"   Run manually: launchctl load {plist_path}")
        return False


def install_linux():
    """Install as systemd user service"""
    service_content = """[Unit]
Description=Agent Rules Sync - Synchronize rules across AI coding assistants
After=network.target

[Service]
Type=simple
ExecStart={python_path} -m agent_rules_sync
Restart=always
RestartSec=10
StandardOutput=append:{log_dir}/daemon.log
StandardError=append:{log_dir}/daemon.log

[Install]
WantedBy=default.target
"""

    python_path = sys.executable
    log_dir = str(Path.home() / ".config" / "agent-rules-sync")

    # Create log directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)

    service_path = service_dir / "agent-rules-sync.service"

    service_content = service_content.format(python_path=python_path, log_dir=log_dir)

    with open(service_path, 'w') as f:
        f.write(service_content)

    # Enable and start the service
    try:
        subprocess.run(['systemctl', '--user', 'daemon-reload'],
                       capture_output=True)
        subprocess.run(['systemctl', '--user', 'enable', 'agent-rules-sync.service'],
                       check=True, capture_output=True)
        subprocess.run(['systemctl', '--user', 'start', 'agent-rules-sync.service'],
                       check=True, capture_output=True)
        print(f"✓ Linux systemd daemon installed and started")
        print(f"  Service: agent-rules-sync.service (user)")
        print(f"  Service file: {service_path}")
        print(f"  Check status: systemctl --user status agent-rules-sync")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Could not install systemd service: {e}")
        print(f"   Try manually: systemctl --user enable {service_path}")
        return False


def install_windows():
    """Install as Windows background daemon (via Python)"""
    daemon_script = str(Path.home() / ".config" / "agent-rules-sync" / "run_daemon.py")
    Path(daemon_script).parent.mkdir(parents=True, exist_ok=True)

    script_content = f'''#!/usr/bin/env python3
import sys
import os
os.chdir(os.path.expanduser("~"))
from agent_rules_sync import AgentRulesSync
syncer = AgentRulesSync()
syncer.daemon_start()
'''

    with open(daemon_script, 'w') as f:
        f.write(script_content)

    # Create batch file to run at startup
    startup_dir = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_dir.mkdir(parents=True, exist_ok=True)

    batch_file = startup_dir / "agent-rules-sync.bat"

    batch_content = f'''@echo off
python -m agent_rules_sync
'''

    with open(batch_file, 'w') as f:
        f.write(batch_content)

    print(f"✓ Windows daemon configured")
    print(f"  Batch file: {batch_file}")
    print(f"  Service will start on next login")
    print(f"  To start now, run: python -m agent_rules_sync")

    return True


def main():
    """Install daemon based on platform"""
    print("\nInstalling Agent Rules Sync as background daemon...\n")

    system = platform.system()

    if system == "Darwin":
        # macOS
        success = install_macos()
    elif system == "Linux":
        # Linux
        success = install_linux()
    elif system == "Windows":
        # Windows
        success = install_windows()
    else:
        print(f"⚠️  Unknown platform: {system}")
        print("   Run manually: python -m agent_rules_sync")
        success = False

    if success:
        print("\n✓ Agent Rules Sync daemon is now running and will auto-start on system boot")
        print("\nUseful commands:")
        print("  agent-rules-sync status    # Check daemon status")
        print("  agent-rules-sync stop      # Stop daemon")
        print("  agent-rules-sync watch     # Watch in foreground")

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
