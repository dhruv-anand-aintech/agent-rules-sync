#!/usr/bin/env python3
"""
Agent Skills Sync - Synchronize skills across AI coding assistants

Skills are directory-based: each skill is a folder containing SKILL.md and
optional assets (scripts, references, etc.). This module syncs user-level
skills across Cursor, Claude Code, Codex, Gemini Antigravity, OpenCode, and
the shared ~/.agents/skills path.

Storage locations by framework:
- Cursor: ~/.cursor/skills/, ~/.cursor/skills-cursor/
- Claude Code: ~/.claude/skills/
- Codex: ~/.codex/skills/ (or $CODEX_HOME/skills)
- Gemini Antigravity: ~/.gemini/antigravity/skills/
- OpenCode: ~/.config/opencode/skills/
- Shared (Codex, OpenCode, Claude-compatible): ~/.agents/skills/

Note: Plugin-installed skills (e.g. .claude/plugins/cache/, .codex/vendor_imports/)
are NOT synced - they are managed by each framework's plugin/marketplace system.
"""

import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path


class AgentSkillsSync:
    """Manages synchronization of skills across AI coding assistants."""

    SKILL_MD = "SKILL.md"
    IGNORE_PREFIXES = (".git", "__pycache__", ".", "vendor_imports")

    def __init__(self, config_dir=None):
        """Initialize with config in ~/.config/agent-rules-sync/ (or custom)."""
        self.config_dir = config_dir or (Path.home() / ".config" / "agent-rules-sync")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.master_skills_dir = self.config_dir / "skills"
        self.master_skills_dir.mkdir(exist_ok=True)
        self.backup_dir = self.config_dir / "skill_backups"
        self.backup_dir.mkdir(exist_ok=True)

        # Resolve CODEX_HOME for Codex skills path
        codex_home = os.environ.get("CODEX_HOME")
        if codex_home:
            codex_skills = Path(codex_home).expanduser() / "skills"
        else:
            codex_skills = Path.home() / ".codex" / "skills"

        self.frameworks = {
            "cursor": {
                "name": "Cursor",
                "path": Path.home() / ".cursor" / "skills",
                "description": "Cursor global skills",
            },
            "cursor-skills-cursor": {
                "name": "Cursor Skills-Cursor",
                "path": Path.home() / ".cursor" / "skills-cursor",
                "description": "Cursor skills-cursor (plugin-compatible)",
            },
            "claude": {
                "name": "Claude Code",
                "path": Path.home() / ".claude" / "skills",
                "description": "Claude Code user skills",
            },
            "codex": {
                "name": "Codex",
                "path": codex_skills,
                "description": "Codex user skills",
            },
            "agents": {
                "name": "Shared Agents",
                "path": Path.home() / ".agents" / "skills",
                "description": "Shared ~/.agents/skills (Codex, OpenCode, Claude)",
            },
            "gemini": {
                "name": "Gemini Antigravity",
                "path": Path.home() / ".gemini" / "antigravity" / "skills",
                "description": "Gemini Antigravity skills",
            },
            "opencode": {
                "name": "OpenCode",
                "path": Path.home() / ".config" / "opencode" / "skills",
                "description": "OpenCode global skills",
            },
        }

        # Load repo paths and add each repo's .claude/skills/ as a framework target.
        # Config: ~/.config/agent-rules-sync/repo_paths.json
        # Format: ["/abs/path/to/repo", "~/relative/path"]
        self._load_repo_framework_paths()

    def _load_repo_framework_paths(self):
        """Add configured repos' .claude/skills/ dirs as sync targets."""
        import json
        repo_paths_file = self.config_dir / "repo_paths.json"
        if not repo_paths_file.exists():
            return
        try:
            repo_paths = json.loads(repo_paths_file.read_text())
            for repo_path in repo_paths:
                repo = Path(repo_path).expanduser().resolve()
                if repo.is_dir():
                    fw_id = f"repo:{repo.name}"
                    self.frameworks[fw_id] = {
                        "name": f"Repo: {repo.name}",
                        "path": repo / ".claude" / "skills",
                        "description": f"Project .claude/skills for {repo.name}",
                    }
        except Exception:
            pass

    def _is_valid_skill_dir(self, path):
        """Return True if path is a skill directory (contains SKILL.md)."""
        return path.is_dir() and (path / self.SKILL_MD).exists()

    def _list_skills_in_dir(self, base_path):
        """List valid skill names in a directory."""
        if not base_path.exists():
            return set()
        names = set()
        for item in base_path.iterdir():
            if item.is_dir() and not item.name.startswith(self.IGNORE_PREFIXES):
                if self._is_valid_skill_dir(item):
                    names.add(item.name)
        return names

    def _get_all_skill_names(self):
        """Union of skill names from master and all framework directories."""
        names = self._list_skills_in_dir(self.master_skills_dir)
        for fw in self.frameworks.values():
            names.update(self._list_skills_in_dir(fw["path"]))
        return names

    def _skill_dir_hash(self, skill_path):
        """Compute content hash of a skill directory for change detection."""
        if not skill_path.exists() or not self._is_valid_skill_dir(skill_path):
            return None
        hasher = hashlib.sha256()
        for f in sorted(skill_path.rglob("*")):
            if f.is_file() and not any(
                p.startswith(".") or p == "__pycache__" for p in f.parts
            ):
                hasher.update(str(f.relative_to(skill_path)).encode())
                hasher.update(f.read_bytes())
        return hasher.hexdigest()

    def _get_newest_skill_source(self, skill_name):
        """
        Return (path, mtime) of the skill dir with newest SKILL.md.
        Prefer master, then check frameworks.
        """
        candidates = []
        master_path = self.master_skills_dir / skill_name
        if self._is_valid_skill_dir(master_path):
            mtime = (master_path / self.SKILL_MD).stat().st_mtime
            candidates.append((master_path, mtime))

        for fw in self.frameworks.values():
            skill_path = fw["path"] / skill_name
            if self._is_valid_skill_dir(skill_path):
                mtime = (skill_path / self.SKILL_MD).stat().st_mtime
                candidates.append((skill_path, mtime))

        if not candidates:
            return None
        return max(candidates, key=lambda x: x[1])

    def _backup_skill_dir(self, skill_path, framework_id):
        """Create timestamped backup of a skill directory."""
        if not skill_path.exists():
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{framework_id}_{skill_path.name}_{timestamp}"
        try:
            if backup_path.exists():
                shutil.rmtree(backup_path)
            shutil.copytree(skill_path, backup_path, symlinks=True)
            return backup_path
        except Exception:
            return None

    def _copy_skill(self, src, dst, log_callback=None):
        """
        Copy skill directory from src to dst.
        Removes existing dst/skill_name if present, then copies.
        """
        if src == dst:
            return True
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, symlinks=True)
            if log_callback:
                log_callback(f"Copied {src.name} -> {dst}")
            return True
        except Exception as e:
            if log_callback:
                log_callback(f"Error copying {src.name}: {e}")
            return False

    def sync(self, log_callback=None, backup_before_write=True, direction="bidirectional"):
        """
        Sync skills across all frameworks.

        direction:
          "bidirectional" — newest version wins, propagates to all (default)
          "push"          — master → frameworks only (master is source of truth)
          "pull"          — frameworks → master only (aggregate, don't push back)
        """
        log = log_callback or (lambda _: None)

        all_skills = self._get_all_skill_names()
        if not all_skills:
            return

        for skill_name in sorted(all_skills):
            if direction == "push":
                # Master is source of truth — only push master → frameworks
                src_path = self.master_skills_dir / skill_name
                if not self._is_valid_skill_dir(src_path):
                    continue
            elif direction == "pull":
                # Aggregate newest from frameworks → master only, don't push back
                result = self._get_newest_skill_source(skill_name)
                if not result:
                    continue
                src_path, _ = result
                master_dst = self.master_skills_dir / skill_name
                if src_path != master_dst:
                    if backup_before_write and master_dst.exists():
                        self._backup_skill_dir(master_dst, "master")
                    self._copy_skill(src_path, master_dst, log)
                continue  # don't push to frameworks
            else:  # bidirectional
                result = self._get_newest_skill_source(skill_name)
                if not result:
                    continue
                src_path, _ = result

                # Write to master first
                master_dst = self.master_skills_dir / skill_name
                if src_path != master_dst:
                    if backup_before_write and master_dst.exists():
                        self._backup_skill_dir(master_dst, "master")
                    self._copy_skill(src_path, master_dst, log)

            # Propagate master → all frameworks
            for fw_id, fw in self.frameworks.items():
                dst = fw["path"] / skill_name
                if dst.exists() and backup_before_write:
                    self._backup_skill_dir(dst, fw_id)
                self._copy_skill(
                    self.master_skills_dir / skill_name, dst, log
                )

    def delete_skill(self, skill_name, backup=True, log_callback=None):
        """
        Delete a skill from master and all framework directories.

        Returns a dict with keys 'deleted' (list of paths removed) and
        'not_found' (list of locations where the skill didn't exist).
        """
        log = log_callback or (lambda _: None)
        deleted = []
        not_found = []

        locations = {"master": self.master_skills_dir}
        for fw_id, fw in self.frameworks.items():
            locations[fw_id] = fw["path"]

        for loc_id, base in locations.items():
            skill_path = base / skill_name
            if skill_path.exists() and self._is_valid_skill_dir(skill_path):
                if backup:
                    self._backup_skill_dir(skill_path, loc_id)
                try:
                    shutil.rmtree(skill_path)
                    deleted.append(skill_path)
                    log(f"Deleted {skill_name} from {loc_id} ({skill_path})")
                except Exception as e:
                    log(f"Error deleting {skill_name} from {loc_id}: {e}")
            else:
                not_found.append(str(skill_path))

        return {"deleted": deleted, "not_found": not_found}

    def get_watch_paths_and_hashes(self):
        """
        Return dict of {path: hash} for all skill dirs we monitor.
        Used by watch loop for change detection.
        """
        result = {}

        def add_skill_hashes(base):
            if not base.exists():
                return
            for item in base.iterdir():
                if item.is_dir() and self._is_valid_skill_dir(item):
                    h = self._skill_dir_hash(item)
                    if h:
                        result[item] = h

        add_skill_hashes(self.master_skills_dir)
        for fw in self.frameworks.values():
            add_skill_hashes(fw["path"])

        return result

    def skills_changed(self, old_hashes):
        """Check if any monitored skill dir has changed since old_hashes."""
        current = self.get_watch_paths_and_hashes()
        if set(current.keys()) != set(old_hashes.keys()):
            return True
        for path, h in current.items():
            if path in old_hashes and old_hashes[path] != h:
                return True
        return False
