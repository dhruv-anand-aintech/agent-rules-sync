#!/usr/bin/env python3
"""
Agent Settings Sync - Sync portable Claude settings + hooks to configured repos.

Reads ~/.claude/settings.json (global), builds a portable version for each
repo's .claude/settings.json:
  - Strips machine-specific keys (statusLine, spinnerVerbs, etc.)
  - Strips permission rules containing absolute machine paths
  - Rewrites hook commands to use repo-relative paths where possible
  - Keeps plugins, MCP tools, permissions that are portable

Configured via:
  ~/.config/agent-rules-sync/repo_paths.json   — list of repo paths to sync to
  ~/.config/agent-rules-sync/settings_sync.json — optional overrides (see below)

settings_sync.json schema:
  {
    "strip_keys": ["statusLine", "hooks", ...],        // top-level keys to strip entirely
    "strip_path_prefixes": ["/Users/", "/opt/..."],    // prefixes marking machine-specific rules
    "sync_hooks": true,                                 // whether to include hooks (default true)
    "hook_script_dir": ".claude/hooks"                 // repo-relative dir for hook scripts
  }
"""

import json
import hashlib
import shutil
from pathlib import Path


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
]

# Absolute path prefixes that make a permission rule machine-specific
DEFAULT_STRIP_PATH_PREFIXES = [
    "/Users/",
    "/home/",
    "/opt/homebrew/",
    "/usr/local/",
    "/Applications/",
]

# Hook script dir inside global ~/.claude/hooks/
GLOBAL_HOOKS_DIR = Path.home() / ".claude" / "hooks"

# Default repo-relative location for hook scripts
DEFAULT_HOOK_SCRIPT_DIR = ".claude/hooks"


class AgentSettingsSync:
    """Syncs a portable Claude settings.json (with hooks) to configured repos."""

    def __init__(self, config_dir=None):
        self.config_dir = config_dir or (Path.home() / ".config" / "agent-rules-sync")
        self.source = Path.home() / ".claude" / "settings.json"
        self._load_config()
        self._load_repo_paths()

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
        self.hook_script_dir = cfg.get("hook_script_dir", DEFAULT_HOOK_SCRIPT_DIR)

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

    def _rewrite_hook_command(self, command: str, repo: Path) -> str | None:
        """
        Rewrite a hook command so it works from a repo checkout.

        Rules:
        - If command references a script in ~/.claude/hooks/ (absolute or tilde),
          rewrite to repo-relative .claude/hooks/<script> (script will be copied).
        - If command references any other machine-specific absolute path, return None.
        - Otherwise return command unchanged.
        """
        # Match both absolute path and tilde form
        hooks_variants = [
            str(GLOBAL_HOOKS_DIR) + "/",   # /Users/foo/.claude/hooks/
            "~/.claude/hooks/",             # tilde form
        ]
        for variant in hooks_variants:
            if variant in command:
                return command.replace(variant, self.hook_script_dir + "/")
        # Check for other machine-specific absolute paths
        for prefix in self.strip_path_prefixes:
            if prefix in command:
                return None
        # Also strip tilde-prefixed ~/.claude/ references (not hooks) as they
        # are machine-home-specific — except ~/.claude/hooks/ handled above
        if "~/.claude/" in command:
            return None
        return command

    def _copy_hook_scripts(self, repo: Path, hook_scripts: list[str], log):
        """Copy referenced hook scripts from ~/.claude/hooks/ into repo's hook dir."""
        dest_dir = repo / self.hook_script_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        for script_name in hook_scripts:
            src = GLOBAL_HOOKS_DIR / script_name
            dst = dest_dir / script_name
            if src.exists():
                if not dst.exists() or src.read_bytes() != dst.read_bytes():
                    shutil.copy2(src, dst)
                    dst.chmod(0o755)
                    log(f"[settings] {repo.name}: copied hook script {script_name}")

    def _make_portable_hooks(self, hooks: dict, repo: Path, log) -> dict | None:
        """
        Rewrite hooks block for the repo.
        Returns portable hooks dict and populates self._hook_scripts_to_copy.
        """
        if not self.sync_hooks or not hooks:
            return None

        self._hook_scripts_to_copy = []
        portable = {}

        for event, matchers in hooks.items():
            portable_matchers = []
            for matcher_block in matchers:
                portable_hooks_list = []
                for hook in matcher_block.get("hooks", []):
                    if hook.get("type") != "command":
                        # prompt/agent hooks — keep as-is if no machine paths
                        portable_hooks_list.append(hook)
                        continue
                    cmd = hook.get("command", "")
                    new_cmd = self._rewrite_hook_command(cmd, repo)
                    if new_cmd is None:
                        log(f"[settings] {repo.name}: skipping non-portable hook in {event}: {cmd[:60]}")
                        continue
                    # Track any hook scripts to copy
                    for variant in [str(GLOBAL_HOOKS_DIR) + "/", "~/.claude/hooks/"]:
                        if variant in cmd:
                            script_name = cmd.split(variant)[1].split()[0]
                            if script_name not in self._hook_scripts_to_copy:
                                self._hook_scripts_to_copy.append(script_name)
                            break
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

    def _make_portable(self, settings: dict, repo: Path, log) -> dict:
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
                        # Strip machine-specific dirs (keep /tmp etc.)
                        portable_perms["additionalDirectories"] = [
                            d for d in perm_val
                            if not any(d.startswith(p) for p in self.strip_path_prefixes)
                        ]
                    else:
                        portable_perms[perm_key] = perm_val
                result["permissions"] = portable_perms
            elif key == "hooks":
                portable_hooks = self._make_portable_hooks(value, repo, log)
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
        """Sync portable settings to all configured repos. Returns list of (repo, status)."""
        log = log_callback or (lambda _: None)

        if not self.source.exists():
            log("Source ~/.claude/settings.json not found, skipping settings sync")
            return []

        try:
            raw = json.loads(self.source.read_text())
        except Exception as e:
            log(f"Failed to parse ~/.claude/settings.json: {e}")
            return []

        results = []
        for repo in self.repo_paths:
            self._hook_scripts_to_copy = []
            portable = self._make_portable(raw, repo, log)
            portable_json = json.dumps(portable, indent=2) + "\n"

            dest = repo / ".claude" / "settings.json"
            dest.parent.mkdir(parents=True, exist_ok=True)

            if dest.exists() and dest.read_text() == portable_json:
                log(f"[settings] {repo.name}: up to date")
                results.append((repo, "up_to_date"))
            else:
                dest.write_text(portable_json)
                log(f"[settings] {repo.name}: synced")
                results.append((repo, "synced"))

            # Copy hook scripts referenced in the hooks block
            if self._hook_scripts_to_copy:
                self._copy_hook_scripts(repo, self._hook_scripts_to_copy, log)

        return results

    def get_watch_hashes(self) -> dict:
        """Return {path: hash} for change detection — watch source + hook scripts."""
        result = {}
        if self.source.exists():
            result[self.source] = self._file_hash(self.source)
        if GLOBAL_HOOKS_DIR.exists():
            for f in GLOBAL_HOOKS_DIR.iterdir():
                if f.is_file():
                    result[f] = self._file_hash(f)
        return result

    def settings_changed(self, old_hashes: dict) -> bool:
        return self.get_watch_hashes() != old_hashes
