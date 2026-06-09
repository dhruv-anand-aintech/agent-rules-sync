#!/usr/bin/env python3
"""Launchd foreground entrypoint for Agent Rules Sync."""

from __future__ import annotations

from pathlib import Path
import os
import sys


def _resolve_repo_root() -> Path:
    """Resolve repository root from env or local file layout."""
    repo_env = os.environ.get("AGENT_RULES_SYNC_REPO")
    if repo_env:
        return Path(repo_env).expanduser().resolve()

    candidate = Path(__file__).resolve().parent.parent
    if (candidate / "agent_rules_sync.py").exists():
        return candidate

    # Fallback for manual invocation; keep it explicit so behavior is easy to diagnose.
    return Path.cwd().resolve()


def main() -> None:
    os.environ.setdefault("ARSRULES_DISK_LIMIT_BYTES", str(5 * 1024 * 1024 * 1024))
    os.environ.setdefault("ARSRULES_LAUNCHD_LABEL", "com.local.agent-rules-sync")

    repo_root = _resolve_repo_root()
    sys.path.insert(0, str(repo_root))

    from agent_rules_sync import AgentRulesSync  # noqa: E402

    syncer = AgentRulesSync()
    syncer._rotate_log_if_needed()
    syncer.watch()


if __name__ == "__main__":
    main()
