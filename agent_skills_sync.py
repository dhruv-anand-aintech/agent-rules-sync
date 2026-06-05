#!/usr/bin/env python3
"""
Agent Skills Sync - Synchronize skills across AI coding assistants

Skills are directory-based: each skill is a folder containing SKILL.md and
optional assets (scripts, references, etc.). This module syncs user-level
skills across Cursor, Claude Code, Codex, Antigravity CLI, Gemini Antigravity,
OpenCode, and
the shared ~/.agents/skills path.

Storage locations by framework:
- Cursor: ~/.cursor/skills/, ~/.cursor/skills-cursor/
- Claude Code: ~/.claude/skills/
- Codex: ~/.codex/skills/ (or $CODEX_HOME/skills)
- Antigravity CLI: ~/.gemini/antigravity-cli/plugins/agent-rules-sync/skills/
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

from agent_antigravity_cli import ensure_plugin as ensure_antigravity_cli_plugin
from agent_exclusions import ExclusionRules


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
        self.exclusions = ExclusionRules(self.config_dir)

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
            "antigravity-cli": {
                "name": "Antigravity CLI",
                "path": Path.home() / ".gemini" / "antigravity-cli" / "plugins" / "agent-rules-sync" / "skills",
                "description": "Antigravity CLI plugin skills",
            },
            "gemini-antigravity": {
                "name": "Gemini Antigravity",
                "path": Path.home() / ".gemini" / "antigravity" / "skills",
                "description": "Gemini Antigravity skills",
            },
            "gemini-cli": {
                "name": "Gemini CLI",
                "path": Path.home() / ".gemini" / "skills",
                "description": "Gemini CLI skills",
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

    def _has_valid_skill_frontmatter(self, skill_md):
        """Return True when SKILL.md starts with a non-empty YAML frontmatter block."""
        if not skill_md.is_file():
            return False
        try:
            lines = skill_md.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            return False
        if len(lines) < 3 or lines[0].strip() != "---":
            return False
        try:
            closing_index = next(
                i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"
            )
        except StopIteration:
            return False
        frontmatter = [line.strip() for line in lines[1:closing_index]]
        has_name = False
        has_description = False
        for line in frontmatter:
            if line.startswith("name:"):
                has_name = bool(line.split(":", 1)[1].strip().strip("'\""))
            if line.startswith("description:"):
                value = line.split(":", 1)[1].strip()
                if value in {">", "|", ">-", "|-"}:
                    has_description = True
                else:
                    has_description = bool(value.strip("'\""))
        return has_name and has_description

    def _is_valid_skill_dir(self, path):
        """Return True if path is a skill directory with valid SKILL.md metadata."""
        return path.is_dir() and self._has_valid_skill_frontmatter(path / self.SKILL_MD)

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
        for fw_id, fw in self.frameworks.items():
            excluded = self._excluded_skills_for_framework(fw_id)
            names.update(self._list_skills_in_dir(fw["path"]) - excluded)
        return names

    def _skill_dir_hash(self, skill_path):
        """Compute a cheap change-detection token for a skill directory.

        Uses mtime+size of each file rather than reading file contents — this is
        called every 3s in the poll loop across all skill dirs, so avoiding
        read_bytes() cuts CPU dramatically. A content-level hash is only needed
        when we actually sync, not to detect whether syncing is needed.
        """
        if not skill_path.exists() or not self._is_valid_skill_dir(skill_path):
            return None
        hasher = hashlib.sha256()
        for f in sorted(skill_path.rglob("*")):
            rel = f.relative_to(skill_path)
            if f.is_file() and not any(
                p.startswith(".") or p == "__pycache__" for p in rel.parts
            ):
                hasher.update(str(rel).encode())
                st = f.stat()
                hasher.update(f"{st.st_mtime_ns}:{st.st_size}".encode())
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

        for fw_id, fw in self.frameworks.items():
            if skill_name in self._excluded_skills_for_framework(fw_id):
                continue
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

    def _remove_existing_path(self, path):
        """Remove a file, directory, or symlink at path."""
        try:
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            return True
        except FileNotFoundError:
            return True
        except Exception:
            return False

    def _copy_skill(self, src, dst, log_callback=None):
        """
        Copy skill directory from src to dst.
        Stage the copy beside the destination, then replace the old directory.
        This avoids deleting a valid skill when the copy fails, for example
        because the disk is full.
        """
        if src == dst:
            return True
        tmp_dst = dst.parent / f".{dst.name}.tmp-sync"
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if tmp_dst.exists() or tmp_dst.is_symlink():
                if not self._remove_existing_path(tmp_dst):
                    raise OSError(f"Could not remove temporary destination: {tmp_dst}")
            shutil.copytree(src, tmp_dst, symlinks=True)
            if dst.exists() or dst.is_symlink():
                if not self._remove_existing_path(dst):
                    raise OSError(f"Could not remove existing destination: {dst}")
            tmp_dst.replace(dst)
            if log_callback:
                log_callback(f"Copied {src.name} -> {dst}")
            return True
        except Exception as e:
            if tmp_dst.exists() or tmp_dst.is_symlink():
                self._remove_existing_path(tmp_dst)
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
        self._remove_excluded_skills(backup_before_write, log)
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
                if skill_name in self._excluded_skills_for_framework(fw_id):
                    dst = fw["path"] / skill_name
                    if dst.exists() or dst.is_symlink():
                        if backup_before_write:
                            self._backup_skill_dir(dst, fw_id)
                        self._remove_existing_path(dst)
                        log(f"Excluded {skill_name} from {fw_id} ({dst})")
                    continue
                if fw_id == "antigravity-cli":
                    ensure_antigravity_cli_plugin()
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
                    if not self._remove_existing_path(skill_path):
                        raise OSError(f"Could not remove {skill_path}")
                    deleted.append(skill_path)
                    log(f"Deleted {skill_name} from {loc_id} ({skill_path})")
                except Exception as e:
                    log(f"Error deleting {skill_name} from {loc_id}: {e}")
            else:
                not_found.append(str(skill_path))

        return {"deleted": deleted, "not_found": not_found}

    def _repo_for_framework(self, fw_id):
        if not fw_id.startswith("repo:") or fw_id not in self.frameworks:
            return None
        path = self.frameworks[fw_id]["path"]
        if path.name == "skills" and path.parent.name == ".claude":
            return path.parent.parent
        return None

    def _excluded_skills_for_framework(self, fw_id):
        return self.exclusions.for_target(
            "skills",
            fw_id,
            self._repo_for_framework(fw_id),
        )

    def _remove_excluded_skills(self, backup_before_write, log):
        for fw_id, fw in self.frameworks.items():
            for skill_name in self._excluded_skills_for_framework(fw_id):
                skill_path = fw["path"] / skill_name
                if not (skill_path.exists() or skill_path.is_symlink()):
                    continue
                if backup_before_write:
                    self._backup_skill_dir(skill_path, fw_id)
                if self._remove_existing_path(skill_path):
                    log(f"Excluded {skill_name} from {fw_id} ({skill_path})")

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
        for fw_id, fw in self.frameworks.items():
            excluded = self._excluded_skills_for_framework(fw_id)
            if not excluded:
                add_skill_hashes(fw["path"])
                continue
            if not fw["path"].exists():
                continue
            for skill_name in excluded:
                excluded_path = fw["path"] / skill_name
                if excluded_path.exists() or excluded_path.is_symlink():
                    result[excluded_path] = "excluded-present"
            for item in fw["path"].iterdir():
                if item.name in excluded:
                    continue
                if item.is_dir() and self._is_valid_skill_dir(item):
                    h = self._skill_dir_hash(item)
                    if h:
                        result[item] = h

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
