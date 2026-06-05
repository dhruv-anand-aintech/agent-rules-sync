#!/usr/bin/env python3
"""Shared exclusion rules for agent-rules-sync components."""

import json
from pathlib import Path


class ExclusionRules:
    """Loads global and repo-local exclude rules.

    Global file: ~/.config/agent-rules-sync/excludes.json

    Example:
      {
        "skills": {
          "agents": {
            "codex": ["canvas"],
            "agents": ["canvas"],
            "opencode": ["canvas"]
          },
          "repos": {
            "my-repo": ["local-only-skill"]
          }
        },
        "mcp": {
          "agents": {
            "opencode": ["large-debug-server"]
          }
        }
      }

    Repo-local file: <repo>/.agent-rules-sync-excludes.json
      {"skills": ["canvas"], "mcp": ["local-server"]}
    """

    REPO_FILENAME = ".agent-rules-sync-excludes.json"

    def __init__(self, config_dir=None):
        self.config_dir = config_dir or (Path.home() / ".config" / "agent-rules-sync")
        self.data = self._read_json(self.config_dir / "excludes.json")

    def _read_json(self, path: Path) -> dict:
        try:
            if path.exists():
                data = json.loads(path.read_text())
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    def _names_from(self, value) -> set[str]:
        if isinstance(value, list):
            return {str(v) for v in value}
        if isinstance(value, dict):
            for key in ("exclude", "names"):
                names = value.get(key)
                if isinstance(names, list):
                    return {str(v) for v in names}
        return set()

    def for_target(self, component: str, target_id: str, repo: Path | None = None) -> set[str]:
        names = set()
        component_cfg = self.data.get(component, {})

        if isinstance(component_cfg, dict):
            agents = component_cfg.get("agents", {})
            if isinstance(agents, dict):
                names.update(self._names_from(agents.get("*")))
                names.update(self._names_from(agents.get(target_id)))

            targets = component_cfg.get("targets", {})
            if isinstance(targets, dict):
                names.update(self._names_from(targets.get("*")))
                names.update(self._names_from(targets.get(target_id)))

            if repo is not None:
                repos = component_cfg.get("repos", {})
                if isinstance(repos, dict):
                    names.update(self._names_from(repos.get("*")))
                    names.update(self._names_from(repos.get(repo.name)))
                    names.update(self._names_from(repos.get(str(repo))))

        if repo is not None:
            repo_cfg = self._read_json(repo / self.REPO_FILENAME)
            names.update(self._names_from(repo_cfg.get(component)))

        return names
