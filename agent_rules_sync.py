#!/usr/bin/env python3
"""
Agent Rules Sync - Synchronize rules and skills across AI coding assistants

Simple usage:
    agent-rules-sync              # Start auto-sync daemon
    agent-rules-sync status       # Check sync status
    agent-rules-sync stop         # Stop daemon

Edit your rules in any location:
    ~/.claude/CLAUDE.md
    ~/.cursor/rules/global.mdc
    ~/.gemini/GEMINI.md
    ~/.config/opencode/AGENTS.md

Skills sync across:
    ~/.cursor/skills/, ~/.claude/skills/, ~/.codex/skills/,
    ~/.gemini/antigravity/skills/, ~/.config/opencode/skills/, ~/.agents/skills/

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

from agent_skills_sync import AgentSkillsSync
from agent_settings_sync import AgentSettingsSync
from agent_sync_config import load_config, save_config, SyncConfig, DEFAULT_CONFIG, run_wizard


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

        # State file to track previous sync (for detecting deletions)
        self.state_file = self.config_dir / "sync_state.txt"

        # Stop event for graceful Windows daemon shutdown
        self.stop_event = threading.Event()

        # Skills sync (syncs skills across Cursor, Claude, Codex, Gemini, OpenCode)
        self.skills_sync = AgentSkillsSync(config_dir=self.config_dir)

        # Settings sync (syncs portable ~/.claude/settings.json to configured repos)
        self.settings_sync = AgentSettingsSync(config_dir=self.config_dir)

        # Sync direction config
        self.sync_config = load_config(self.config_dir)

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
            },
            "config-agents": {
                "name": "Config Agents",
                "path": Path.home() / ".config" / "agents" / "AGENTS.md",
                "description": "Config agents configuration",
            },
            "codex": {
                "name": "Codex",
                "path": Path.home() / ".codex" / "AGENTS.md",
                "description": "Codex agent configuration",
            },
            "config": {
                "name": "Config AGENTS",
                "path": Path.home() / ".config" / "AGENTS.md",
                "description": "Config root AGENTS file",
            },
            "agent": {
                "name": "Local Agent",
                "path": Path.home() / ".agent" / "AGENTS.md",
                "description": "Local agent configuration",
            },
            "agent-alt": {
                "name": "Local Agent Alt",
                "path": Path.home() / ".agent" / "AGENT.md",
                "description": "Local agent configuration (alternate)",
            }
        }

        # Load repo paths and add each repo's CLAUDE.md as a sync target.
        # Uses the same repo_paths.json as agent_skills_sync.
        self._load_repo_agent_paths()

    def _load_repo_agent_paths(self):
        """Add configured repos' CLAUDE.md as rules sync targets."""
        import json
        repo_paths_file = self.config_dir / "repo_paths.json"
        if not repo_paths_file.exists():
            return
        try:
            repo_paths = json.loads(repo_paths_file.read_text())
            for repo_path in repo_paths:
                repo = Path(repo_path).expanduser().resolve()
                if repo.is_dir():
                    agent_id = f"repo:{repo.name}"
                    self.agents[agent_id] = {
                        "name": f"Repo: {repo.name}",
                        "path": repo / "CLAUDE.md",
                        "description": f"Project CLAUDE.md for {repo.name}",
                    }
        except Exception:
            pass

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
        if agent_name in self.agents:
            return self.agents[agent_name]["name"].replace(" (", "").replace(")", "")
        return agent_name

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

    def _migrate_from_old_version(self):
        """Migrate from versions without state file support."""
        # If master exists but state file doesn't, this is an upgrade
        if self.master_file.exists() and not self.state_file.exists():
            try:
                # Initialize state from current master file
                with open(self.master_file, 'r') as f:
                    content = f.read()
                shared_rules = self._extract_shared_rules(content)
                self._save_shared_rules_state(shared_rules)
                self._log_message("Migrated to version with state tracking")
            except Exception as e:
                self._log_error(f"Migration error: {e}")

    def _load_previous_shared_rules(self):
        """Load shared rules from previous sync."""
        if not self.state_file.exists():
            return None
        try:
            with open(self.state_file, 'r') as f:
                content = f.read()
            return self._extract_shared_rules(content)
        except Exception:
            return None

    def _save_shared_rules_state(self, shared_rules):
        """Save current shared rules state."""
        try:
            with open(self.state_file, 'w') as f:
                f.write("# Shared Rules\n")
                for rule in sorted(shared_rules):
                    f.write(f"{rule}\n")
        except Exception:
            pass

    def sync(self):
        """
        Sync rules with smart deletion detection.

        Strategy:
        - Load previous state to detect deletions
        - Union of all current rules (additions from any file)
        - Subtract any rules that were in previous state but removed from ANY file
        """
        try:
            self._ensure_master_exists()
            self._migrate_from_old_version()

            # Step 1: Load previous shared rules state
            previous_shared = self._load_previous_shared_rules()

            # Step 2: Read master file
            with open(self.master_file, 'r') as f:
                master_content = f.read()

            master_shared = self._extract_shared_rules(master_content)
            master_agent_rules = {}
            for agent_id in self.agents:
                master_agent_rules[agent_id] = self._extract_agent_rules(master_content, agent_id)

            # Step 3: Collect all shared rules (union for additions)
            all_shared_rules = set(master_shared)

            for agent_id, config in self.agents.items():
                agent_path = config["path"]
                if agent_path.exists():
                    try:
                        with open(agent_path, 'r') as f:
                            agent_content = f.read()

                        # Union: Add any rules from this agent
                        agent_shared = self._extract_shared_rules(agent_content)
                        all_shared_rules.update(agent_shared)

                        # Merge agent-specific rules
                        agent_specific = self._extract_agent_rules(agent_content, agent_id)
                        master_agent_rules[agent_id].update(agent_specific)
                    except Exception:
                        pass

            # Step 4: Detect deletions
            # If we have previous state, remove rules that were deleted from ANY file
            if previous_shared is not None:
                # Check if any previously-existing rule is now missing from ANY file
                rules_to_delete = set()
                self._log_message(f"Checking deletions: {len(previous_shared)} in prev, {len(master_shared)} in master, {len(all_shared_rules)} in union")

                for rule in previous_shared:
                    # Check if rule was deleted from master
                    if rule not in master_shared:
                        rules_to_delete.add(rule)
                        self._log_message(f"Deletion detected from master: {rule[:50]}...")
                        continue

                    # Check if rule was deleted from any agent
                    for agent_id, config in self.agents.items():
                        if config["path"].exists():
                            try:
                                with open(config["path"], 'r') as f:
                                    agent_content = f.read()
                                agent_shared = self._extract_shared_rules(agent_content)
                                if rule not in agent_shared:
                                    rules_to_delete.add(rule)
                                    self._log_message(f"Deletion detected from {agent_id}: {rule[:50]}...")
                                    break
                            except Exception:
                                pass

                # Remove deleted rules
                if rules_to_delete:
                    self._log_message(f"Removing {len(rules_to_delete)} deleted rules")
                all_shared_rules -= rules_to_delete

            master_shared = all_shared_rules

            # Step 3: Rebuild and write master file
            master_lines = ["# Shared Rules"]
            master_lines.extend(sorted(master_shared))

            for agent_id in self.agents:
                agent_heading = f"## {self._get_agent_heading(agent_id)} Specific"
                master_lines.append("")
                master_lines.append(agent_heading)
                master_lines.extend(sorted(master_agent_rules[agent_id]))

            master_text = '\n'.join(master_lines) + '\n'

            if self.master_file.exists():
                backup_path = self._backup_file(self.master_file, "master")
                if backup_path:
                    self._log_message(f"Backed up master: {backup_path.name}")

            with open(self.master_file, 'w') as f:
                f.write(master_text)

            # Step 4: Write agent files — direction controls push/pull/bidirectional
            rules_direction = self.sync_config.direction("rules")
            rules_enabled = self.sync_config.enabled("rules")

            if rules_enabled and rules_direction in ("bidirectional", "push"):
                for agent_id, config in self.agents.items():
                    agent_path = config["path"]
                    try:
                        agent_path.parent.mkdir(parents=True, exist_ok=True)

                        if agent_path.exists():
                            backup_path = self._backup_file(agent_path, agent_id)
                            if backup_path:
                                self._log_message(f"Backed up {agent_id}: {backup_path.name}")

                        content = self._build_file_content(
                            master_shared,
                            master_agent_rules[agent_id],
                            agent_id
                        )
                        with open(agent_path, 'w') as f:
                            f.write(content)
                    except Exception as e:
                        self._log_error(f"Error syncing {agent_id}: {e}")

            # Step 5: Save current state for next sync's deletion detection
            self._save_shared_rules_state(master_shared)

            # Step 6: Sync skills across frameworks (respects direction config)
            if self.sync_config.enabled("skills"):
                try:
                    direction = self.sync_config.direction("skills")
                    self.skills_sync.sync(
                        log_callback=self._log_message,
                        backup_before_write=True,
                        direction=direction,
                    )
                except Exception as e:
                    self._log_error(f"Skills sync error: {e}")

            # Step 7: Sync portable settings + hooks to configured repos
            if self.sync_config.enabled("settings"):
                try:
                    self.settings_sync.sync(log_callback=self._log_message)
                except Exception as e:
                    self._log_error(f"Settings sync error: {e}")
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
        # Store initial hashes for rules
        file_hashes = {}
        file_hashes["master"] = self._get_file_hash(self.master_file)
        for agent_id, config in self.agents.items():
            file_hashes[agent_id] = self._get_file_hash(config["path"])

        # Store initial hashes for skills and settings
        skill_hashes = self.skills_sync.get_watch_paths_and_hashes()
        settings_hashes = self.settings_sync.get_watch_hashes()

        print(f"🔄 Watching for changes (every {interval}s)...")
        print(f"Edit rules or skills in any agent - changes auto-sync!\n")
        self._log_message("Watch started")

        # Initial sync to ensure rules and skills are propagated
        self.sync()
        self._log_message("Initial sync complete")

        try:
            while True:
                time.sleep(interval)

                # Check if any rules file changed
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

                # Check if any skills changed
                if self.skills_sync.skills_changed(skill_hashes):
                    changed = True
                    skill_hashes = self.skills_sync.get_watch_paths_and_hashes()

                # Check if settings or hook scripts changed
                if self.settings_sync.settings_changed(settings_hashes):
                    changed = True
                    settings_hashes = self.settings_sync.get_watch_hashes()

                if changed:
                    self.sync()
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    msg = f"✓ Synced rules and skills across all agents"
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

        # Skills status
        skill_count = len(
            self.skills_sync._list_skills_in_dir(self.skills_sync.master_skills_dir)
        )
        print(f"📚 Skills: {skill_count} synced to {len(self.skills_sync.frameworks)} frameworks")
        print(f"   Master: {self.skills_sync.master_skills_dir}")
        print(f"   Backups: {self.skills_sync.backup_dir}")
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
                skill_hashes = self.skills_sync.get_watch_paths_and_hashes()
                settings_hashes = self.settings_sync.get_watch_hashes()

                # Initial sync
                self.sync()

                # Use stop_event to allow graceful shutdown
                while not self.stop_event.is_set():
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

                    if self.skills_sync.skills_changed(skill_hashes):
                        changed = True
                        skill_hashes = self.skills_sync.get_watch_paths_and_hashes()

                    if self.settings_sync.settings_changed(settings_hashes):
                        changed = True
                        settings_hashes = self.settings_sync.get_watch_hashes()

                    if changed:
                        self.sync()
                        self._log_message("✓ Synced rules and skills")

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
                # Windows: Signal stop event (thread checks this flag)
                self.stop_event.set()
                print(f"✓ Daemon stop requested (PID: {pid})")
            else:
                # Unix: Send SIGTERM
                os.kill(pid, signal.SIGTERM)
                print(f"✓ Daemon stopped (PID: {pid})")
        except (OSError, ValueError) as e:
            print(f"❌ Error stopping daemon: {e}")
        finally:
            # Always cleanup PID file, even on error
            try:
                self.pid_file.unlink()
            except OSError:
                pass


SYNC_SCOPES = ["rules", "skills", "settings", "all"]
COMMANDS = ["sync", "setup", "status", "stop", "watch", "daemon"]


def _run_sync(syncer, scopes):
    """Run a one-shot sync for the given scopes."""
    logs = []
    log = lambda m: logs.append(m) or print(f"  {m}")

    if "rules" in scopes or "all" in scopes:
        print("⟳ Syncing rules...")
        syncer.sync()  # rules sync is baked into sync()

    if "skills" in scopes or "all" in scopes:
        print("⟳ Syncing skills...")
        try:
            syncer.skills_sync.sync(log_callback=log, backup_before_write=False)
        except Exception as e:
            print(f"  ✗ Skills error: {e}")

    if "settings" in scopes or "all" in scopes:
        print("⟳ Syncing settings...")
        try:
            syncer.settings_sync.sync(log_callback=log)
        except Exception as e:
            print(f"  ✗ Settings error: {e}")

    print("✓ Done")


def main():
    parser = argparse.ArgumentParser(
        prog='agent-sync',
        description='Sync rules, skills, and settings across AI coding assistants',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  agent-sync                         Start/ensure daemon is running
  agent-sync sync [scope ...]        One-shot sync (scopes: rules skills settings all)
  agent-sync setup                   TUI wizard to configure sync directions
  agent-sync status                  Check daemon and sync status
  agent-sync stop                    Stop daemon
  agent-sync watch                   Watch in foreground (debugging)

Sync scope examples:
  agent-sync sync                    Sync everything (default)
  agent-sync sync rules              Sync only CLAUDE.md / rules files
  agent-sync sync skills             Sync only skills directories
  agent-sync sync settings           Sync only .claude/settings.json + hooks
  agent-sync sync rules skills       Sync rules and skills
        """
    )

    parser.add_argument('command', nargs='?', default='daemon',
                        choices=COMMANDS,
                        help='Command to run (default: daemon)')
    parser.add_argument('scopes', nargs='*',
                        metavar='SCOPE',
                        help=f'Scopes for sync command: {", ".join(SYNC_SCOPES)}')

    args = parser.parse_args()
    syncer = AgentRulesSync()

    if args.command == 'sync':
        scopes = args.scopes if args.scopes else ['all']
        # Validate scopes
        invalid = [s for s in scopes if s not in SYNC_SCOPES]
        if invalid:
            print(f"✗ Unknown scopes: {', '.join(invalid)}")
            print(f"  Valid scopes: {', '.join(SYNC_SCOPES)}")
            sys.exit(1)
        _run_sync(syncer, scopes)

    elif args.command == 'setup':
        from agent_sync_config import run_wizard, load_config
        existing = load_config(syncer.config_dir)
        cfg = run_wizard(syncer.config_dir, existing=existing)
        if cfg:
            syncer.sync_config = cfg

    elif args.command == 'watch':
        syncer.watch()

    elif args.command == 'status':
        syncer.status()

    elif args.command == 'stop':
        syncer.daemon_stop()

    else:  # daemon (default)
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
