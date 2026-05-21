#!/usr/bin/env python3
"""
Agent MCP Sync - Synchronize MCP server configurations across agents.

Targets:
- Claude Code: ~/.claude.json
- Cursor: ~/.cursor/mcp.json
- Gemini CLI: ~/.gemini/mcp.json
- Antigravity CLI: ~/.gemini/antigravity-cli/plugins/agent-rules-sync/mcp_config.json
- OpenCode: ~/.config/opencode/opencode.json
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
import re
import toml

from agent_antigravity_cli import ensure_plugin as ensure_antigravity_cli_plugin

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
            "antigravity-cli": {
                "name": "Antigravity CLI",
                "path": Path.home() / ".gemini" / "antigravity-cli" / "plugins" / "agent-rules-sync" / "mcp_config.json",
            },
            "claude-desktop": {
                "name": "Claude Desktop",
                "path": self._get_claude_desktop_path(),
            },
            "opencode": {
                "name": "OpenCode",
                "path": Path.home() / ".config" / "opencode" / "opencode.json",
                "mcp_key": "mcp",
                "from_internal": self._to_opencode_format,
                "from_file": self._from_opencode_file,
            },
            "codex": {
                "name": "Codex",
                "path": Path.home() / ".codex" / "config.toml",
                "mcp_key": "mcp_servers",
                "from_internal": self._to_codex_toml_format,
                "from_file": self._from_codex_file,
                "format": "toml",
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

    def _to_opencode_format(self, servers: dict) -> dict:
        """Convert internal format to OpenCode's mcp format."""
        result = {}
        for name, cfg in servers.items():
            new_cfg = dict(cfg)
            if "url" in new_cfg:
                new_cfg["type"] = "remote"
                new_cfg["enabled"] = new_cfg.get("enabled", True)
            elif "command" in new_cfg:
                command = new_cfg.get("command")
                args = new_cfg.pop("args", [])
                if isinstance(command, list):
                    new_cfg["command"] = command
                elif command:
                    new_cfg["command"] = [command, *args]
                new_cfg["type"] = "local"
                new_cfg["enabled"] = new_cfg.get("enabled", True)
            result[name] = new_cfg
        return result

    def _from_opencode_file(self, path: Path, info: dict) -> dict:
        try:
            data = json.loads(path.read_text())
            raw = data.get(info.get("mcp_key", "mcp"), {})
            result = {}
            for name, cfg in raw.items():
                if not isinstance(cfg, dict):
                    continue
                new_cfg = dict(cfg)
                server_type = new_cfg.pop("type", None)
                new_cfg.pop("enabled", None)
                if server_type == "local" and isinstance(new_cfg.get("command"), list):
                    command = new_cfg["command"]
                    if command:
                        new_cfg["command"] = command[0]
                        if len(command) > 1:
                            new_cfg["args"] = command[1:]
                result[name] = new_cfg
            return result
        except Exception:
            return {}

    def _to_codex_toml_format(self, servers: dict) -> dict:
        """Convert internal format to Codex's config.toml MCP format."""
        result = {}
        for name, cfg in servers.items():
            new_cfg = {}
            if "command" in cfg:
                new_cfg["type"] = "stdio"
                new_cfg["command"] = cfg.get("command")
                if "args" in cfg and cfg["args"]:
                    new_cfg["args"] = cfg["args"]
            if "url" in cfg:
                new_cfg["type"] = "remote"
                new_cfg["url"] = cfg.get("url")
            if "env" in cfg and cfg["env"]:
                new_cfg["env"] = cfg["env"]
            if "headers" in cfg and cfg["headers"]:
                new_cfg["http_headers"] = cfg["headers"]
            # preserve any extra keys if present
            for key, value in cfg.items():
                if key in {"type", "command", "args", "url", "env", "headers", "description"}:
                    continue
                if key not in new_cfg:
                    new_cfg[key] = value
            result[name] = new_cfg
        return result

    def _from_codex_file(self, path: Path, info: dict) -> dict:
        try:
            data = toml.loads(path.read_text())
            mcp_key = info.get("mcp_key", "mcp_servers")
            raw = data.get(mcp_key, {})
            result = {}
            for name, cfg in raw.items():
                if not isinstance(cfg, dict):
                    continue
                new_cfg = dict(cfg)
                if "http_headers" in new_cfg:
                    new_cfg["headers"] = new_cfg.pop("http_headers")
                # keep legacy type/url/command/args/env exactly as-is
                result[name] = new_cfg
            return result
        except Exception:
            return {}

    def _quote_toml_key(self, key: str) -> str:
        return json.dumps(key)

    def _format_toml_value(self, value):
        if isinstance(value, str):
            return json.dumps(value)
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, list):
            return json.dumps(value)
        if isinstance(value, dict):
            # Inline table representation keeps the file easy for Codex to parse.
            return "{" + ", ".join(
                f"{json.dumps(k)} = {self._format_toml_value(v)}" for k, v in value.items()
            ) + "}"
        if value is None:
            return "null"
        return json.dumps(value)

    def _update_toml_mcp_section(self, path: Path, servers: dict):
        text = path.read_text() if path.exists() else ""
        lines = text.splitlines()
        cleaned = []
        skipping = False

        for line in lines:
            stripped = line.strip()
            if re.match(r"^\[mcp_servers(\.|\])", stripped):
                skipping = True
                continue
            if skipping:
                if stripped.startswith("[") and stripped.endswith("]"):
                    skipping = False
                else:
                    continue
            if not skipping:
                cleaned.append(line)

        output = [l for l in cleaned if l.strip()]
        if output and output[-1].strip() != "":
            output.append("")

        for name in sorted(servers):
            cfg = servers[name]
            quoted_name = self._quote_toml_key(name)
            output.append(f'[mcp_servers.{quoted_name}]')
            for k, v in cfg.items():
                if k == "http_headers":
                    continue
                output.append(f"{k} = {self._format_toml_value(v)}")
            for k, v in cfg.items():
                if k != "http_headers" or not isinstance(v, dict):
                    continue
                output.append(f"[mcp_servers.{quoted_name}.http_headers]")
                for hk, hv in v.items():
                    output.append(f"{hk} = {self._format_toml_value(hv)}")
            output.append("")

        output_text = "\n".join(output).rstrip() + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output_text)

    def _get_mcp_servers(self, path: Path, info: dict = None) -> dict:
        """Extract MCP servers from a file."""
        if not path.exists():
            return {}
        try:
            if info and info.get("format") == "toml" and info.get("from_file"):
                return info["from_file"](path, info)
            if info and info.get("from_file"):
                return info["from_file"](path, info)
            data = json.loads(path.read_text())
            mcp_key = info.get("mcp_key", "mcpServers") if info else "mcpServers"
            if mcp_key in data:
                return data[mcp_key]
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
                servers = self._get_mcp_servers(path, info)
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
                if label == "antigravity-cli":
                    ensure_antigravity_cli_plugin()
                self._update_target(path, all_servers, label, log, info)

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

    def _update_target(self, path: Path, servers: dict, label: str, log, info: dict = None):
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

        new_data = dict(current_data)
        mcp_key = info.get("mcp_key", "mcpServers") if info else "mcpServers"
        output_servers = servers
        if info and "from_internal" in info:
            output_servers = info["from_internal"](servers)
        new_data[mcp_key] = output_servers

        new_json = json.dumps(new_data, indent=2) + "\n"

        if info and info.get("format") == "toml":
            self._update_toml_mcp_section(path, output_servers)
            log(f"[mcp] Synced {label} ({path.name})")
            return

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
