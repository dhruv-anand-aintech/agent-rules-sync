#!/usr/bin/env python3
"""
Agent Rules Sync - Synchronize rules across AI coding assistants

Simple usage:
    agent-rules-sync              # Start auto-sync daemon
    agent-rules-sync status       # Check sync status
    agent-rules-sync stop         # Stop daemon

Edit your rules in any location:
    ~/.claude/CLAUDE.md
    ~/.cursor/rules/global.mdc
    ~/.gemini/GEMINI.md
    ~/.config/opencode/AGENTS.md

Changes are automatically synced to all agents!
"""

import argparse
import os
import sys
import time
import hashlib
import threading
from pathlib import Path
from datetime import datetime
import shutil
import signal


class AgentRulesSync:
    """Manages synchronization of rules across AI coding assistants."""

    def __init__(self):
        """Initialize the sync manager with config in ~/.config/agent-rules-sync/"""
        # Store config in user's .config directory (hidden)
        self.config_dir = Path.home() / ".config" / "agent-rules-sync"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Master rules file (hidden from user)
        self.master_file = self.config_dir / "RULES.md"

        # Backup directory
        self.backup_dir = self.config_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        # PID file for daemon mode
        self.pid_file = self.config_dir / "daemon.pid"
        self.watch_flag_file = self.config_dir / "watching"

        # Agent configuration files (user-facing)
        self.agents = {
            "claude": {
                "name": "Claude Code",
                "path": Path.home() / ".claude" / "CLAUDE.md",
                "description": "Claude Code global configuration",
            },
            "cursor": {
                "name": "Cursor",
                "path": Path.home() / ".cursor" / "rules" / "global.mdc",
                "description": "Cursor global rules",
            },
            "gemini": {
                "name": "Gemini Antigravity",
                "path": Path.home() / ".gemini" / "GEMINI.md",
                "description": "Gemini Antigravity global rules",
            },
            "opencode": {
                "name": "OpenCode",
                "path": Path.home() / ".config" / "opencode" / "AGENTS.md",
                "description": "OpenCode global agents configuration",
            }
        }

    def _get_file_hash(self, filepath):
        """Calculate SHA256 hash of a file."""
        if not filepath.exists():
            return None
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _backup_file(self, filepath, agent_name):
        """Create a backup of a file before modifying it."""
        if not filepath.exists():
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{agent_name}_{timestamp}.md"
        backup_path = self.backup_dir / backup_filename
        try:
            shutil.copy2(filepath, backup_path)
            return backup_path
        except Exception:
            return None

    def _extract_shared_rules(self, content):
        """Extract rules from 'Shared Rules' section."""
        rules = set()
        lines = content.split('\n')
        in_shared = False
        for line in lines:
            if line.strip() == '# Shared Rules':
                in_shared = True
                continue
            if in_shared and line.strip().startswith('##'):
                break
            if in_shared and line.strip().startswith('-'):
                rules.add(line.strip())
        return rules

    def _extract_agent_rules(self, content, agent_name):
        """Extract rules from agent-specific section."""
        rules = set()
        agent_heading = f"## {self._get_agent_heading(agent_name)} Specific"
        lines = content.split('\n')
        in_section = False
        for line in lines:
            if line.strip() == agent_heading:
                in_section = True
                continue
            if in_section and line.strip().startswith('##'):
                break
            if in_section and line.strip().startswith('-'):
                rules.add(line.strip())
        return rules

    def _get_agent_heading(self, agent_name):
        """Get display name for agent heading."""
        headings = {
            "claude": "Claude Code",
            "cursor": "Cursor",
            "gemini": "Gemini",
            "opencode": "OpenCode"
        }
        return headings.get(agent_name, agent_name)

    def _build_file_content(self, shared_rules, agent_rules, agent_name):
        """Build file content with shared and agent-specific sections."""
        lines = ["# Shared Rules"]
        lines.extend(sorted(shared_rules))

        agent_heading = f"## {self._get_agent_heading(agent_name)} Specific"
        lines.append("")
        lines.append(agent_heading)
        lines.extend(sorted(agent_rules))

        return '\n'.join(lines) + '\n'

    def _ensure_master_exists(self):
        """Ensure master file exists with all sections (create if needed)."""
        if not self.master_file.exists():
            # Build initial master with all sections
            lines = ["# Shared Rules"]

            # Try to extract shared rules from first available agent
            for agent_id, config in self.agents.items():
                if config["path"].exists():
                    try:
                        with open(config["path"], 'r') as f:
                            content = f.read()
                        shared = self._extract_shared_rules(content)
                        lines.extend(sorted(shared))
                        break
                    except Exception:
                        pass

            # Add agent-specific sections
            for agent_id in self.agents:
                agent_heading = f"## {self._get_agent_heading(agent_id)} Specific"
                lines.append("")
                lines.append(agent_heading)

            with open(self.master_file, 'w') as f:
                f.write('\n'.join(lines) + '\n')

    def sync(self):
        """Sync rules from all sources to master and back to all agents."""
        try:
            self._ensure_master_exists()

            # Read master
            with open(self.master_file, 'r') as f:
                master_content = f.read()

            # Collect all rules from all agents
            all_agent_content = master_content
            for agent_id, config in self.agents.items():
                if config["path"].exists():
                    try:
                        with open(config["path"], 'r') as f:
                            agent_content = f.read()
                        all_agent_content = self._merge_rules(all_agent_content, agent_content)
                    except Exception:
                        pass

            # Update master with merged rules
            if self.master_file.exists():
                backup_path = self._backup_file(self.master_file, "master")
                if backup_path:
                    self._log_message(f"Backed up master: {backup_path.name}")

            with open(self.master_file, 'w') as f:
                f.write(all_agent_content)

            # Push merged rules to all agents
            for agent_id, config in self.agents.items():
                agent_path = config["path"]
                try:
                    agent_path.parent.mkdir(parents=True, exist_ok=True)

                    if agent_path.exists():
                        backup_path = self._backup_file(agent_path, agent_id)
                        if backup_path:
                            self._log_message(f"Backed up {agent_id}: {backup_path.name}")

                    with open(agent_path, 'w') as f:
                        f.write(all_agent_content)
                except Exception:
                    pass
        except Exception as e:
            self._log_error(f"Sync error: {e}")

    def _log_error(self, msg):
        """Log error to daemon log file."""
        try:
            log_file = self.config_dir / "daemon.log"
            with open(log_file, 'a') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] ERROR: {msg}\n")
        except Exception:
            pass

    def _log_message(self, msg):
        """Log message to daemon log file."""
        try:
            log_file = self.config_dir / "daemon.log"
            with open(log_file, 'a') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {msg}\n")
        except Exception:
            pass

    def watch(self, interval=3):
        """Watch for changes and auto-sync."""
        # Store initial hashes
        file_hashes = {}
        file_hashes["master"] = self._get_file_hash(self.master_file)
        for agent_id, config in self.agents.items():
            file_hashes[agent_id] = self._get_file_hash(config["path"])

        print(f"🔄 Watching for changes (every {interval}s)...")
        print(f"Edit rules in any agent file - changes auto-sync!\n")
        self._log_message("Watch started")

        try:
            while True:
                time.sleep(interval)

                # Check if any file changed
                master_hash = self._get_file_hash(self.master_file)
                changed = False

                if master_hash != file_hashes["master"]:
                    changed = True
                    file_hashes["master"] = master_hash

                for agent_id, config in self.agents.items():
                    current_hash = self._get_file_hash(config["path"])
                    if current_hash != file_hashes[agent_id]:
                        changed = True
                        file_hashes[agent_id] = current_hash

                if changed:
                    self.sync()
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    msg = f"✓ Synced rules across all agents"
                    print(f"[{timestamp}] {msg}")
                    self._log_message(msg)

        except KeyboardInterrupt:
            print("\n✓ Watch mode stopped")
            self._log_message("Watch stopped")

    def status(self):
        """Show current status."""
        self._ensure_master_exists()

        print(f"\n{'='*70}")
        print(f"Agent Rules Sync Status")
        print(f"{'='*70}\n")

        print(f"📂 Config: {self.config_dir}\n")

        # Daemon status
        if self.pid_file.exists():
            try:
                with open(self.pid_file) as f:
                    pid = int(f.read().strip())
                print(f"🔄 Daemon status: Running (PID {pid})")
            except Exception:
                print(f"🔄 Daemon status: Unknown")
        else:
            print(f"🔄 Daemon status: Not running")
        print()

        # Master status
        master_hash = self._get_file_hash(self.master_file)
        print(f"📄 Master Rules: {self.master_file}")
        print(f"   Hash: {master_hash[:12] if master_hash else 'N/A'}...")
        print()

        # Agent status
        for agent_id, config in self.agents.items():
            agent_path = config["path"]
            agent_name = config["name"]

            print(f"🤖 {agent_name}")
            print(f"   Path: {agent_path}")

            if agent_path.exists():
                agent_hash = self._get_file_hash(agent_path)
                in_sync = agent_hash == master_hash
                status = "✓ In sync" if in_sync else "⚠️  Out of sync"
                print(f"   Status: {status}")
            else:
                print(f"   Status: ⚠️  Not found")

            print()

        print(f"{'='*70}\n")

    def daemon_start(self):
        """Start daemon (cross-platform)."""
        # Check if already running
        if self.pid_file.exists():
            try:
                with open(self.pid_file) as f:
                    pid_str = f.read().strip()
                    if pid_str:
                        pid = int(pid_str)
                        if sys.platform == "win32":
                            # On Windows, we can't easily check if PID exists
                            print(f"✓ Daemon recorded as running (PID: {pid})")
                            return
                        else:
                            os.kill(pid, 0)  # Check if process exists
                            print(f"✓ Daemon already running (PID: {pid})")
                            return
            except (OSError, ValueError):
                pass

        print("Starting Agent Rules Sync daemon...")

        if sys.platform == "win32":
            # Windows: Run in background thread
            self._daemon_start_windows()
        else:
            # Unix/Linux/Mac: Use fork
            self._daemon_start_unix()

    def _daemon_start_unix(self):
        """Start daemon on Unix/Linux/Mac using fork."""
        pid = os.fork()
        if pid != 0:
            # Parent process
            print(f"✓ Daemon started (PID: {pid})")
            return

        # Child process - become daemon
        os.setsid()
        os.umask(0o022)

        # Redirect output to log file
        log_file = self.config_dir / "daemon.log"
        try:
            with open(log_file, 'a') as f:
                f.write(f"\n--- Session started {datetime.now()} ---\n")

            log_handle = open(log_file, 'a')
            sys.stdout = log_handle
            sys.stderr = log_handle
        except Exception:
            pass

        # Save PID
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))

        # Run watch
        self.watch(interval=3)
        sys.exit(0)

    def _daemon_start_windows(self):
        """Start daemon on Windows using background thread."""
        def daemon_thread():
            try:
                with open(self.pid_file, 'w') as f:
                    f.write(str(os.getpid()))

                log_file = self.config_dir / "daemon.log"
                with open(log_file, 'a') as f:
                    f.write(f"\n--- Session started {datetime.now()} ---\n")

                # Watch without printing to console
                file_hashes = {}
                file_hashes["master"] = self._get_file_hash(self.master_file)
                for agent_id, config in self.agents.items():
                    file_hashes[agent_id] = self._get_file_hash(config["path"])

                while True:
                    time.sleep(3)

                    master_hash = self._get_file_hash(self.master_file)
                    changed = False

                    if master_hash != file_hashes["master"]:
                        changed = True
                        file_hashes["master"] = master_hash

                    for agent_id, config in self.agents.items():
                        current_hash = self._get_file_hash(config["path"])
                        if current_hash != file_hashes[agent_id]:
                            changed = True
                            file_hashes[agent_id] = current_hash

                    if changed:
                        self.sync()
                        self._log_message("✓ Synced rules")

            except Exception as e:
                self._log_error(str(e))
            finally:
                try:
                    self.pid_file.unlink()
                except Exception:
                    pass

        thread = threading.Thread(target=daemon_thread, daemon=True)
        thread.start()
        print("✓ Daemon started (background thread)")

    def daemon_stop(self):
        """Stop daemon (cross-platform)."""
        if not self.pid_file.exists():
            print("❌ Daemon not running")
            return

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())

            if sys.platform == "win32":
                # Windows: Just remove PID file (thread will clean up)
                print(f"✓ Daemon stop requested (PID: {pid})")
            else:
                # Unix: Send SIGTERM
                os.kill(pid, signal.SIGTERM)
                print(f"✓ Daemon stopped (PID: {pid})")

            self.pid_file.unlink()
        except (OSError, ValueError) as e:
            print(f"❌ Error stopping daemon: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Sync rules across AI coding assistants',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The daemon runs automatically in the background after installation.

Quick usage:
  agent-rules-sync status    # Check daemon status
  agent-rules-sync stop      # Stop daemon
  agent-rules-sync watch     # Watch in foreground (for debugging)

Edit any agent file to sync rules:
  vim ~/.claude/CLAUDE.md
  vim ~/.cursor/rules/global.mdc
  vim ~/.gemini/GEMINI.md

Changes sync automatically within 3 seconds!
        """
    )

    parser.add_argument('command', nargs='?', default='daemon',
                       choices=['daemon', 'watch', 'status', 'stop'],
                       help='Command to execute')

    args = parser.parse_args()

    syncer = AgentRulesSync()

    if args.command == 'watch':
        syncer.watch()
    elif args.command == 'status':
        syncer.status()
    elif args.command == 'stop':
        syncer.daemon_stop()
    else:  # daemon (default)
        # Just ensure daemon is running
        if syncer.pid_file.exists():
            try:
                with open(syncer.pid_file) as f:
                    pid = int(f.read().strip())
                if sys.platform != "win32":
                    os.kill(pid, 0)
                    print(f"✓ Daemon already running (PID: {pid})")
                else:
                    print(f"✓ Daemon recorded as running (PID: {pid})")
                return
            except (OSError, ValueError):
                pass

        syncer.daemon_start()


if __name__ == '__main__':
    main()
