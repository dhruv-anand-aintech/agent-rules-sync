#!/usr/bin/env python3
"""
Agent MCP Sync - Synchronize MCP server configurations across agents.

Targets:
- Claude Code: ~/.claude.json
- Cursor: ~/.cursor/mcp.json
- Gemini CLI: ~/.gemini/mcp.json
- Claude Desktop: ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)
                 ~/.config/Claude/claude_desktop_config.json (Linux)

Project-specific (merged into master, then pushed back if bidirectional):
- Repo: .mcp.json
- Repo: .cursor/mcp.json
- Repo: .gemini/mcp.json
"""

import json
import os
import hashlib
from pathlib import Path
import shutil
from datetime import datetime

class AgentMcpSync:
    """Manages synchronization of MCP server configurations."""

    def __init__(self, config_dir=None):
        self.config_dir = config_dir or (Path.home() / ".config" / "agent-rules-sync")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.master_file = self.config_dir / "mcp.json"
        self.backup_dir = self.config_dir / "mcp_backups"
        self.backup_dir.mkdir(exist_ok=True)

        self.global_sources = {
            "claude-code": {
                "name": "Claude Code",
                "path": Path.home() / ".claude.json",
            },
            "cursor": {
                "name": "Cursor",
                "path": Path.home() / ".cursor" / "mcp.json",
            },
            "gemini": {
                "name": "Gemini CLI",
                "path": Path.home() / ".gemini" / "mcp.json",
            },
            "claude-desktop": {
                "name": "Claude Desktop",
                "path": self._get_claude_desktop_path(),
            }
        }

        self.repo_paths = []
        self._load_repo_paths()

    def _get_claude_desktop_path(self) -> Path:
        import sys
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        elif sys.platform == "win32":
            return Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
        else:
            return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    def _load_repo_paths(self):
        repo_paths_file = self.config_dir / "repo_paths.json"
        if not repo_paths_file.exists():
            return
        try:
            paths = json.loads(repo_paths_file.read_text())
            for p in paths:
                repo = Path(p).expanduser().resolve()
                if repo.is_dir():
                    self.repo_paths.append(repo)
        except Exception:
            pass

    def _get_mcp_servers(self, path: Path) -> dict:
        """Extract mcpServers from a file."""
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
            # Claude Desktop and Cursor usually have mcpServers at top level
            if "mcpServers" in data:
                return data["mcpServers"]
            # Some files might just be the mcpServers object itself if small
            # but we assume the standard wrapped format for now.
            # If it doesn't have mcpServers, maybe it's the object? 
            # Let's be cautious.
            return {}
        except Exception:
            return {}

    def _file_hash(self, path: Path) -> str | None:
        if not path.exists():
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _backup_file(self, path: Path, label: str):
        if not path.exists():
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{label}_{timestamp}.json"
        shutil.copy2(path, backup_path)

    def sync(self, log_callback=None, direction="bidirectional"):
        log = log_callback or (lambda _: None)
        
        # 1. Load current master
        master_data = {}
        if self.master_file.exists():
            try:
                master_data = json.loads(self.master_file.read_text()).get("mcpServers", {})
            except Exception:
                pass

        # 2. Collect from all sources (Union for additions)
        all_servers = dict(master_data)

        # Global sources
        for label, info in self.global_sources.items():
            path = info["path"]
            if path.exists():
                servers = self._get_mcp_servers(path)
                for name, cfg in servers.items():
                    if name not in all_servers or direction != "push":
                        all_servers[name] = cfg

        # Repo sources
        for repo in self.repo_paths:
            repo_mcp_paths = [
                repo / ".mcp.json",
                repo / ".cursor" / "mcp.json",
                repo / ".gemini" / "mcp.json"
            ]
            for path in repo_mcp_paths:
                if path.exists():
                    servers = self._get_mcp_servers(path)
                    for name, cfg in servers.items():
                        if name not in all_servers or direction != "push":
                            all_servers[name] = cfg

        # 3. Save to master
        new_master = {"mcpServers": all_servers}
        new_master_json = json.dumps(new_master, indent=2) + "\n"
        
        if not self.master_file.exists() or self.master_file.read_text() != new_master_json:
            if self.master_file.exists():
                self._backup_file(self.master_file, "master")
            self.master_file.write_text(new_master_json)
            log(f"[mcp] Updated master mcp.json with {len(all_servers)} servers")

        # 4. Push back if bidirectional or push
        if direction in ("bidirectional", "push"):
            for label, info in self.global_sources.items():
                path = info["path"]
                self._update_target(path, all_servers, label, log)

            for repo in self.repo_paths:
                # For repos, we might want to be more selective, but usually 
                # .cursor/mcp.json or .mcp.json should have everything if synced.
                # We'll sync to the same files we read from.
                repo_mcp_paths = [
                    repo / ".mcp.json",
                    repo / ".cursor" / "mcp.json",
                    repo / ".gemini" / "mcp.json"
                ]
                for path in repo_mcp_paths:
                    # Only update if the file already exists or it's a known location we want to populate
                    # For now, let's only update if it exists to avoid cluttering every repo with 3 files.
                    if path.exists():
                         self._update_target(path, all_servers, f"repo:{repo.name}", log)

    def _update_target(self, path: Path, servers: dict, label: str, log):
        if not path.parent.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                return

        current_data = {}
        if path.exists():
            try:
                current_data = json.loads(path.read_text())
            except Exception:
                pass

        # We keep other keys (like OAuth session in ~/.claude.json) and only update mcpServers
        new_data = dict(current_data)
        new_data["mcpServers"] = servers
        
        new_json = json.dumps(new_data, indent=2) + "\n"
        
        if not path.exists() or path.read_text() != new_json:
            if path.exists():
                self._backup_file(path, label)
            path.write_text(new_json)
            log(f"[mcp] Synced {label} ({path.name})")

    def get_watch_hashes(self) -> dict:
        hashes = {}
        if self.master_file.exists():
            hashes[self.master_file] = self._file_hash(self.master_file)
        
        for label, info in self.global_sources.items():
            path = info["path"]
            if path.exists():
                hashes[path] = self._file_hash(path)
        
        for repo in self.repo_paths:
            repo_mcp_paths = [
                repo / ".mcp.json",
                repo / ".cursor" / "mcp.json",
                repo / ".gemini" / "mcp.json"
            ]
            for path in repo_mcp_paths:
                if path.exists():
                    hashes[path] = self._file_hash(path)
        return hashes

    def mcp_changed(self, old_hashes: dict) -> bool:
        return self.get_watch_hashes() != old_hashes
