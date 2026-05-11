#!/usr/bin/env python3
"""
Agent Guardian - macOS watchdog for agent-rules-sync.
Monitors the daemon and shows a popup if it's down or erroring.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

class AgentGuardian:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "agent-rules-sync"
        self.pid_file = self.config_dir / "daemon.pid"
        self.log_file = self.config_dir / "daemon.log"
        self.last_error_count = self._get_error_count()
        self.last_popup_time = 0
        self.popup_cooldown = 300 # 5 minutes

    def _get_error_count(self):
        if not self.log_file.exists():
            return 0
        try:
            content = self.log_file.read_text()
            return content.count("ERROR:")
        except Exception:
            return 0

    def is_daemon_running(self):
        if not self.pid_file.exists():
            return False
        try:
            pid = int(self.pid_file.read_text().strip())
            # Check if process exists
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            return False

    def show_popup(self, message):
        now = time.time()
        if now - self.last_popup_time < self.popup_cooldown:
            return

        self.last_popup_time = now
        
        applescript = f'''
        set result to display dialog "{message}" with title "Agent Sync Guardian" buttons {{"Inspect", "Restart", "Dismiss"}} default button "Restart" with icon caution
        return button returned of result
        '''
        
        try:
            result = subprocess.check_output(['osascript', '-e', applescript]).decode('utf-8').strip()
            
            if result == "Inspect":
                subprocess.run(['open', str(self.log_file)])
            elif result == "Restart":
                self.restart_daemon()
        except subprocess.CalledProcessError:
            # User clicked cancel or closed dialog
            pass

    def restart_daemon(self):
        # Use the agent-sync command to stop and start
        try:
            subprocess.run(['agent-sync', 'stop'], capture_output=True)
            time.sleep(1)
            subprocess.run(['agent-sync'], capture_output=True)
            # Notify success
            subprocess.run(['osascript', '-e', 'display notification "Agent Sync Daemon restarted successfully." with title "Agent Sync Guardian"'])
        except Exception as e:
            subprocess.run(['osascript', '-e', f'display notification "Failed to restart daemon: {e}" with title "Agent Sync Guardian"'])

    def run(self):
        print(f"Guardian started at {datetime.now()}")
        while True:
            time.sleep(10) # Check every 10 seconds
            
            # Check if running
            if not self.is_daemon_running():
                self.show_popup("Agent Sync Daemon is NOT running.")
                continue

            # Check for new errors
            current_errors = self._get_error_count()
            if current_errors > self.last_error_count:
                new_errors = current_errors - self.last_error_count
                self.last_error_count = current_errors
                self.show_popup(f"Agent Sync Daemon detected {new_errors} new errors.")

if __name__ == "__main__":
    if sys.platform != "darwin":
        print("Guardian is only supported on macOS.")
        sys.exit(1)
        
    guardian = AgentGuardian()
    guardian.run()
