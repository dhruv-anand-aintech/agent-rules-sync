#!/usr/bin/env python3
"""
Agent Rules Sync - Cross-platform Uninstall Script
Works on macOS, Linux, and Windows
"""

import os
import sys
import platform
import subprocess
from pathlib import Path


def stop_daemon():
    """Attempt to stop the daemon gracefully."""
    print("Stopping daemon...")
    try:
        subprocess.run(["agent-rules-sync", "stop"], capture_output=True, timeout=5)
    except Exception:
        pass


def uninstall_macos():
    """Uninstall daemon from macOS (launchd)."""
    print("Unloading macOS launchd service...")
    plist = Path.home() / "Library" / "LaunchAgents" / "com.local.agent-rules-sync.plist"
    
    if plist.exists():
        try:
            subprocess.run(["launchctl", "unload", str(plist)], capture_output=True, timeout=5)
        except Exception:
            pass
        try:
            plist.unlink()
        except Exception:
            pass


def uninstall_linux():
    """Uninstall daemon from Linux (systemd)."""
    print("Stopping systemd service...")
    
    # Stop service
    try:
        subprocess.run(["systemctl", "--user", "stop", "agent-rules-sync.service"],
                      capture_output=True, timeout=5)
    except Exception:
        pass
    
    # Disable service
    try:
        subprocess.run(["systemctl", "--user", "disable", "agent-rules-sync.service"],
                      capture_output=True, timeout=5)
    except Exception:
        pass
    
    # Reload daemon
    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"],
                      capture_output=True, timeout=5)
    except Exception:
        pass
    
    # Remove service file
    service_file = Path.home() / ".config" / "systemd" / "user" / "agent-rules-sync.service"
    if service_file.exists():
        try:
            service_file.unlink()
        except Exception:
            pass


def uninstall_windows():
    """Uninstall daemon from Windows (Task Scheduler + startup folder)."""
    print("Removing Windows startup/scheduler entries...")
    
    # Try to delete Task Scheduler task
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq*agent-rules-sync*"],
            capture_output=True,
            timeout=5
        )
    except Exception:
        pass
    
    # Try to delete scheduled task
    try:
        subprocess.run(
            ["schtasks", "/delete", "/tn", "agent-rules-sync", "/f"],
            capture_output=True,
            timeout=5
        )
    except Exception:
        pass
    
    # Remove batch file from startup folder (old method)
    appdata = os.getenv("APPDATA", "")
    if appdata:
        batch_file = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "agent-rules-sync.bat"
        if batch_file.exists():
            try:
                batch_file.unlink()
            except Exception:
                pass


def remove_pip_package():
    """Uninstall pip package."""
    print("Removing pip package...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "agent-rules-sync"],
                      capture_output=True, timeout=30)
    except Exception:
        print("⚠️  Could not uninstall pip package. Try manually:")
        print("   pip uninstall agent-rules-sync")


def remove_config_directory():
    """Remove config directory."""
    print("Removing config directory...")
    config_dir = Path.home() / ".config" / "agent-rules-sync"
    if config_dir.exists():
        try:
            import shutil
            shutil.rmtree(config_dir)
        except Exception:
            print(f"⚠️  Could not remove {config_dir}. Try manually:")
            print(f"   rm -rf {config_dir}")


def main():
    """Main uninstall procedure."""
    print("\n🗑️  Uninstalling Agent Rules Sync...\n")
    
    system = platform.system()
    
    # Platform-specific uninstall
    if system == "Darwin":
        # macOS
        stop_daemon()
        uninstall_macos()
    elif system == "Linux":
        # Linux
        stop_daemon()
        uninstall_linux()
    elif system == "Windows":
        # Windows
        uninstall_windows()
    else:
        print(f"⚠️  Unknown platform: {system}")
        print("   Please manually remove the daemon service")
    
    # Common cleanup
    remove_pip_package()
    remove_config_directory()
    
    print("\n✓ Agent Rules Sync uninstalled successfully\n")
    print("Your agent rule files are preserved at:")
    print("  ~/.claude/CLAUDE.md")
    print("  ~/.cursor/rules/global.mdc")
    print("  ~/.gemini/GEMINI.md")
    print("  ~/.config/opencode/AGENTS.md")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nUninstall cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during uninstall: {e}")
        sys.exit(1)
