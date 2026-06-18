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
from agent_exclusions import ExclusionRules

class AgentMcpSync:
    """Manages synchronization of MCP server configurations."""

    def __init__(self, config_dir=None):
        self.config_dir = config_dir or (Path.home() / ".config" / "agent-rules-sync")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.master_file = self.config_dir / "mcp.json"
        self.backup_dir = self.config_dir / "mcp_backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.exclusions = ExclusionRules(self.config_dir)

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
        self.plugin_mcp_paths = self._discover_plugin_mcp_paths()

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

    def _discover_plugin_mcp_paths(self) -> list[Path]:
        plugin_root = Path(__file__).resolve().parent / "plugins"
        if not plugin_root.exists():
            return []
        return sorted(plugin_root.glob("*/.mcp.json"))

    def _repo_mcp_paths(self, repo: Path) -> list[Path]:
        return [
            repo / ".mcp.json",
            repo / ".cursor" / "mcp.json",
            repo / ".gemini" / "mcp.json",
        ]

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
        if path.exists() and path.read_text() == output_text:
            return False
        path.write_text(output_text)
        return True

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

    def _get_plugin_mcp_servers(self, path: Path) -> dict:
        """Extract plugin MCP servers and resolve relative paths for global use."""
        servers = self._get_mcp_servers(path)
        base_dir = path.parent
        result = {}
        for name, cfg in servers.items():
            if not isinstance(cfg, dict):
                continue
            new_cfg = dict(cfg)
            cwd = new_cfg.pop("cwd", None)
            cwd_path = Path(cwd) if cwd else base_dir
            if not cwd_path.is_absolute():
                cwd_path = (base_dir / cwd_path).resolve()

            args = new_cfg.get("args")
            if isinstance(args, list):
                new_cfg["args"] = [
                    str((cwd_path / arg).resolve())
                    if isinstance(arg, str) and (arg.startswith("./") or arg.startswith("../"))
                    else arg
                    for arg in args
                ]

            command = new_cfg.get("command")
            if isinstance(command, str) and (command.startswith("./") or command.startswith("../")):
                new_cfg["command"] = str((cwd_path / command).resolve())

            result[name] = new_cfg
        return result

    def _file_hash(self, path: Path) -> str | None:
        if not path.exists():
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _data_hash(self, data) -> str:
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def _json_equal(self, left, right) -> bool:
        return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(
            right, sort_keys=True, separators=(",", ":")
        )

    def _watch_hash_for_target(
        self,
        path: Path,
        label: str,
        info: dict | None = None,
        repo: Path | None = None,
    ) -> str | None:
        if not path.exists():
            return None
        try:
            servers = self._get_mcp_servers(path, info)
            excluded = self.exclusions.for_target("mcp", label, repo)
            normalized = {
                name: cfg for name, cfg in servers.items() if name not in excluded
            }
            return self._data_hash(normalized)
        except Exception:
            return self._file_hash(path)

    def _backup_file(self, path: Path, label: str):
        if not path.exists():
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{label}_{timestamp}.json"
        shutil.copy2(path, backup_path)

    def _master_is_newest(self):
        """
        Return True if master mcp.json has a strictly newer mtime than
        every agent/repo MCP config file.  When True, master is
        authoritative and its deletions propagate.
        """
        if not self.master_file.exists():
            return False
        master_mtime = self.master_file.stat().st_mtime

        for info in self.global_sources.values():
            path = info["path"]
            if path.exists() and path.stat().st_mtime > master_mtime:
                return False

        for repo in self.repo_paths:
            for path in self._repo_mcp_paths(repo):
                if path.exists() and path.stat().st_mtime > master_mtime:
                    return False

        for path in self.plugin_mcp_paths:
            if path.exists() and path.stat().st_mtime > master_mtime:
                return False

        return True

    def sync(self, log_callback=None, direction="bidirectional"):
        log = log_callback or (lambda _: None)

        # 1. Load current master
        master_data = {}
        if self.master_file.exists():
            try:
                master_data = json.loads(self.master_file.read_text()).get("mcpServers", {})
            except Exception:
                pass

        if direction == "push":
            # Master is source of truth — push to all, no merging
            all_servers = dict(master_data)
        elif direction == "pull":
            # Aggregate from agents into master, don't push back
            all_servers = dict(master_data)
            for label, info in self.global_sources.items():
                path = info["path"]
                if path.exists():
                    servers = self._get_mcp_servers(path, info)
                    for name, cfg in servers.items():
                        all_servers[name] = cfg
            for repo in self.repo_paths:
                for path in self._repo_mcp_paths(repo):
                    if path.exists():
                        servers = self._get_mcp_servers(path)
                        for name, cfg in servers.items():
                            all_servers[name] = cfg
            for path in self.plugin_mcp_paths:
                servers = self._get_plugin_mcp_servers(path)
                for name, cfg in servers.items():
                    all_servers[name] = cfg
        else:
            # Bidirectional — mtime decides who wins
            if self._master_is_newest():
                # Master was edited most recently: its contents are authoritative
                # (deletions from master propagate to all agents)
                all_servers = dict(master_data)
                log(f"[mcp] Master is newest — pushing to all agents")
            else:
                # One or more agent/repo files are newer: union-merge all
                # sources into master (additions from agents flow in)
                all_servers = dict(master_data)
                for label, info in self.global_sources.items():
                    path = info["path"]
                    if path.exists():
                        servers = self._get_mcp_servers(path, info)
                        for name, cfg in servers.items():
                            all_servers[name] = cfg
                for repo in self.repo_paths:
                    for path in self._repo_mcp_paths(repo):
                        if path.exists():
                            servers = self._get_mcp_servers(path)
                            for name, cfg in servers.items():
                                all_servers[name] = cfg
                for path in self.plugin_mcp_paths:
                    servers = self._get_plugin_mcp_servers(path)
                    for name, cfg in servers.items():
                        all_servers[name] = cfg

        # 3. Save to master
        new_master = {"mcpServers": all_servers}
        new_master_json = json.dumps(new_master, indent=2) + "\n"

        master_changed = True
        if self.master_file.exists():
            try:
                master_changed = not self._json_equal(json.loads(self.master_file.read_text()), new_master)
            except Exception:
                master_changed = self.master_file.read_text() != new_master_json

        if not self.master_file.exists() or master_changed:
            if self.master_file.exists():
                self._backup_file(self.master_file, "master")
            self.master_file.write_text(new_master_json)
            log(f"[mcp] Updated master mcp.json with {len(all_servers)} servers")

        # 4. Push back to agents (skip for pull-only)
        if direction == "pull":
            return

        for label, info in self.global_sources.items():
            path = info["path"]
            if label == "antigravity-cli":
                ensure_antigravity_cli_plugin()
            self._update_target(path, all_servers, label, log, info)

        for repo in self.repo_paths:
            for path in self._repo_mcp_paths(repo):
                if path.exists():
                    self._update_target(path, all_servers, f"repo:{repo.name}", log, repo=repo)

    def _update_target(self, path: Path, servers: dict, label: str, log, info: dict = None, repo: Path = None):
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
        excluded = self.exclusions.for_target("mcp", label, repo)
        target_servers = {
            name: cfg for name, cfg in servers.items() if name not in excluded
        }
        if excluded:
            log(f"[mcp] Excluding {len(excluded)} server(s) from {label}: {', '.join(sorted(excluded))}")

        output_servers = target_servers
        if info and "from_internal" in info:
            output_servers = info["from_internal"](target_servers)
        new_data[mcp_key] = output_servers

        new_json = json.dumps(new_data, indent=2) + "\n"

        if info and info.get("format") == "toml":
            if self._update_toml_mcp_section(path, output_servers):
                log(f"[mcp] Synced {label} ({path.name})")
            return

        json_changed = True
        if path.exists():
            try:
                json_changed = not self._json_equal(json.loads(path.read_text()), new_data)
            except Exception:
                json_changed = path.read_text() != new_json

        if not path.exists() or json_changed:
            if path.exists():
                self._backup_file(path, label)
            path.write_text(new_json)
            log(f"[mcp] Synced {label} ({path.name})")

    def get_watch_hashes(self) -> dict:
        hashes = {}
        if self.master_file.exists():
            try:
                hashes[self.master_file] = self._data_hash(
                    json.loads(self.master_file.read_text()).get("mcpServers", {})
                )
            except Exception:
                hashes[self.master_file] = self._file_hash(self.master_file)
        
        for label, info in self.global_sources.items():
            path = info["path"]
            if path.exists():
                hashes[path] = self._watch_hash_for_target(path, label, info)
        
        for repo in self.repo_paths:
            for path in self._repo_mcp_paths(repo):
                if path.exists():
                    hashes[path] = self._watch_hash_for_target(
                        path, f"repo:{repo.name}", None, repo
                    )

        for path in self.plugin_mcp_paths:
            if path.exists():
                hashes[path] = self._file_hash(path)
        return hashes

    def mcp_changed(self, old_hashes: dict) -> bool:
        return self.get_watch_hashes() != old_hashes
