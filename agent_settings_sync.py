#!/usr/bin/env python3
"""
Agent Settings Sync - Sync portable agent settings + hooks to configured repos.

Supports:
- Claude Code: ~/.claude/settings.json -> repo/.claude/settings.json
- Gemini CLI:  ~/.gemini/settings.json -> repo/.gemini/settings.json

Reads global settings, builds a portable version for each repo:
  - Strips machine-specific keys (statusLine, effortLevel, etc.)
  - Strips permission rules containing absolute machine paths
  - Rewrites hook commands to use repo-relative paths where possible
  - Keeps plugins, MCP tools, permissions that are portable

Configured via:
  ~/.config/agent-rules-sync/repo_paths.json   — list of repo paths to sync to
  ~/.config/agent-rules-sync/settings_sync.json — optional overrides
"""

import json
import hashlib
import shutil
from pathlib import Path

from agent_exclusions import ExclusionRules


# Top-level keys that are purely machine-local — omit from repo copy
DEFAULT_STRIP_KEYS = [
    "statusLine",
    "spinnerVerbs",
    "spinnerTipsEnabled",
    "spinnerTipsOverride",
    "autoUpdatesChannel",
    "effortLevel",
    "outputStyle",
    "skipDangerousModePermissionPrompt",
    "skipAutoPermissionPrompt",
    "remote",
    "additionalDirectories",
    "theme",
    "selectedAuthType",
    "security",
]

# Absolute path prefixes that make a permission rule machine-specific
DEFAULT_STRIP_PATH_PREFIXES = [
    "/Users/",
    "/home/",
    "/opt/homebrew/",
    "/usr/local/",
    "/Applications/",
]

# Default sources for settings sync
DEFAULT_SOURCES = {
    "claude": {
        "global_path": Path.home() / ".claude" / "settings.json",
        "repo_rel_path": ".claude/settings.json",
        "hooks_dir": Path.home() / ".claude" / "hooks",
        "repo_hooks_rel": ".claude/hooks"
    },
    "gemini": {
        "global_path": Path.home() / ".gemini" / "settings.json",
        "repo_rel_path": ".gemini/settings.json",
        "hooks_dir": Path.home() / ".gemini" / "hooks",
        "repo_hooks_rel": ".gemini/hooks"
    }
}


class AgentSettingsSync:
    """Syncs portable agent settings (with hooks) to configured repos."""

    def __init__(self, config_dir=None):
        self.config_dir = config_dir or (Path.home() / ".config" / "agent-rules-sync")
        self._load_config()
        self._load_repo_paths()
        self.exclusions = ExclusionRules(self.config_dir)

    def _load_config(self):
        cfg_file = self.config_dir / "settings_sync.json"
        if cfg_file.exists():
            try:
                cfg = json.loads(cfg_file.read_text())
            except Exception:
                cfg = {}
        else:
            cfg = {}

        self.strip_keys = set(cfg.get("strip_keys", DEFAULT_STRIP_KEYS))
        self.strip_path_prefixes = cfg.get("strip_path_prefixes", DEFAULT_STRIP_PATH_PREFIXES)
        self.sync_hooks = cfg.get("sync_hooks", True)

    def _load_repo_paths(self):
        self.repo_paths = []
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

    def _is_machine_specific_rule(self, rule: str) -> bool:
        for prefix in self.strip_path_prefixes:
            if prefix in rule:
                return True
        return False

    def _rewrite_hook_command(self, command: str, repo: Path, source_info: dict) -> str | None:
        """
        Rewrite a hook command so it works from a repo checkout.
        """
        hooks_dir = source_info["hooks_dir"]
        repo_hooks_rel = source_info["repo_hooks_rel"]

        # Match both absolute path and tilde form
        hooks_variants = [
            str(hooks_dir) + "/",
            "~" + str(hooks_dir).replace(str(Path.home()), "") + "/",
        ]
        
        # Add special case for common patterns if they aren't covered
        if "claude" in str(hooks_dir):
            hooks_variants.append("~/.claude/hooks/")
        if "gemini" in str(hooks_dir):
            hooks_variants.append("~/.gemini/hooks/")

        for variant in hooks_variants:
            if variant in command:
                return command.replace(variant, repo_hooks_rel + "/")

        # Check for other machine-specific absolute paths
        for prefix in self.strip_path_prefixes:
            if prefix in command:
                return None
        
        # Strip tilde-prefixed home references
        if "~/" in command and not any(v in command for v in hooks_variants):
            return None
            
        return command

    def _copy_hook_scripts(self, repo: Path, hook_scripts: list[str], source_info: dict, log):
        """Copy referenced hook scripts into repo's hook dir."""
        hooks_dir = source_info["hooks_dir"]
        repo_hooks_rel = source_info["repo_hooks_rel"]
        
        dest_dir = repo / repo_hooks_rel
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        for script_name in hook_scripts:
            src = hooks_dir / script_name
            dst = dest_dir / script_name
            if src.exists():
                if not dst.exists() or src.read_bytes() != dst.read_bytes():
                    shutil.copy2(src, dst)
                    dst.chmod(0o755)
                    log(f"[settings] {repo.name}: copied hook script {script_name}")

    def _make_portable_hooks(self, hooks: dict, repo: Path, source_info: dict, log, agent_name: str = "") -> dict | None:
        """
        Rewrite hooks block for the repo.
        """
        if not self.sync_hooks or not hooks:
            return None

        self._hook_scripts_to_copy = []
        portable = {}
        hooks_dir = source_info["hooks_dir"]
        excluded_hooks = self.exclusions.for_target("hooks", agent_name, repo) if agent_name else set()

        for event, matchers in hooks.items():
            portable_matchers = []
            for matcher_block in matchers:
                portable_hooks_list = []
                for hook in matcher_block.get("hooks", []):
                    if hook.get("type") != "command":
                        portable_hooks_list.append(hook)
                        continue
                    cmd = hook.get("command", "")
                    new_cmd = self._rewrite_hook_command(cmd, repo, source_info)
                    if new_cmd is None:
                        log(f"[settings] {repo.name}: skipping non-portable hook in {event}: {cmd[:60]}")
                        continue

                    # Extract script filename and stem for copy-tracking and exclusion checks
                    script_file = None
                    script_stem = None
                    for variant in [str(hooks_dir) + "/", "~" + str(hooks_dir).replace(str(Path.home()), "") + "/"]:
                        if variant in cmd:
                            raw_arg = cmd.split(variant)[1].split()[0].strip("'\"")
                            script_file = raw_arg
                            script_stem = Path(raw_arg).stem
                            if script_file not in self._hook_scripts_to_copy:
                                self._hook_scripts_to_copy.append(script_file)
                            break

                    # Skip hook if its script stem is in the exclusion list for this agent
                    if script_stem and script_stem in excluded_hooks:
                        log(f"[settings] {repo.name}: excluding hook '{script_stem}' from {agent_name} ({event})")
                        continue

                    rewritten = dict(hook)
                    rewritten["command"] = new_cmd
                    portable_hooks_list.append(rewritten)

                if portable_hooks_list:
                    block = dict(matcher_block)
                    block["hooks"] = portable_hooks_list
                    portable_matchers.append(block)

            if portable_matchers:
                portable[event] = portable_matchers

        return portable if portable else None

    def _make_portable(self, settings: dict, repo: Path, source_info: dict, log, agent_name: str = "") -> dict:
        """Build a portable settings dict for the given repo."""
        result = {}
        for key, value in settings.items():
            if key in self.strip_keys:
                continue
            if key == "permissions":
                portable_perms = {}
                for perm_key, perm_val in value.items():
                    if perm_key == "allow":
                        portable_perms["allow"] = [
                            r for r in perm_val
                            if not self._is_machine_specific_rule(r)
                        ]
                    elif perm_key == "additionalDirectories":
                        portable_perms["additionalDirectories"] = [
                            d for d in perm_val
                            if not any(d.startswith(p) for p in self.strip_path_prefixes)
                        ]
                    else:
                        portable_perms[perm_key] = perm_val
                result["permissions"] = portable_perms
            elif key == "hooks":
                portable_hooks = self._make_portable_hooks(value, repo, source_info, log, agent_name)
                if portable_hooks:
                    result["hooks"] = portable_hooks
            else:
                result[key] = value
        return result

    def _file_hash(self, path: Path) -> str | None:
        if not path.exists():
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def sync(self, log_callback=None):
        """Sync portable settings to all configured repos."""
        log = log_callback or (lambda _: None)
        results = []

        for name, info in DEFAULT_SOURCES.items():
            source = info["global_path"]
            if not source.exists():
                continue

            try:
                raw = json.loads(source.read_text())
            except Exception as e:
                log(f"Failed to parse {source}: {e}")
                continue

            for repo in self.repo_paths:
                self._hook_scripts_to_copy = []
                portable = self._make_portable(raw, repo, info, log, agent_name=name)
                portable_json = json.dumps(portable, indent=2) + "\n"

                dest = repo / info["repo_rel_path"]
                dest.parent.mkdir(parents=True, exist_ok=True)

                if dest.exists() and dest.read_text() == portable_json:
                    log(f"[settings] {repo.name} ({name}): up to date")
                    results.append((repo, f"{name}:up_to_date"))
                else:
                    dest.write_text(portable_json)
                    log(f"[settings] {repo.name} ({name}): synced")
                    results.append((repo, f"{name}:synced"))

                if self._hook_scripts_to_copy:
                    self._copy_hook_scripts(repo, self._hook_scripts_to_copy, info, log)

        return results

    def get_watch_hashes(self) -> dict:
        """Return {path: hash} for change detection."""
        result = {}
        for info in DEFAULT_SOURCES.values():
            source = info["global_path"]
            if source.exists():
                result[source] = self._file_hash(source)
            hooks_dir = info["hooks_dir"]
            if hooks_dir.exists():
                for f in hooks_dir.iterdir():
                    if f.is_file():
                        result[f] = self._file_hash(f)
        return result

    def settings_changed(self, old_hashes: dict) -> bool:
        return self.get_watch_hashes() != old_hashes
