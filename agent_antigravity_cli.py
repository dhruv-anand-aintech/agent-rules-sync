#!/usr/bin/env python3
"""Helpers for the managed Antigravity CLI plugin."""

import json
from pathlib import Path


PLUGIN_NAME = "agent-rules-sync"


def plugin_dir() -> Path:
    return Path.home() / ".gemini" / "antigravity-cli" / "plugins" / PLUGIN_NAME


def ensure_plugin() -> Path:
    """Create the Antigravity CLI plugin marker and standard subdirectories."""
    root = plugin_dir()
    root.mkdir(parents=True, exist_ok=True)
    for name in ("rules", "skills"):
        (root / name).mkdir(exist_ok=True)

    marker = root / "plugin.json"
    if not marker.exists():
        marker.write_text(
            json.dumps(
                {
                    "name": PLUGIN_NAME,
                    "version": "1.0.0",
                    "description": "Rules, skills, and MCP servers managed by agent-rules-sync.",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return root
