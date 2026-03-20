#!/usr/bin/env python3
"""
Sync configuration model, loader, and TUI setup wizard.

Config stored at: ~/.config/agent-rules-sync/sync_config.json

Schema:
  {
    "version": 1,
    "mode": "default" | "per_component",
    "components": {
      "rules":    { "direction": "bidirectional" | "push" | "pull", "enabled": true },
      "skills":   { "direction": "bidirectional" | "push" | "pull", "enabled": true },
      "settings": { "direction": "push",                            "enabled": true },
      "hooks":    { "direction": "push",                            "enabled": true }
    }
  }

Directions:
  bidirectional  — newest version wins; syncs to all locations (rules/skills only)
  push           — master → agents/repos only (master is source of truth)
  pull           — agents → master only (aggregate, don't push back)

Settings and hooks only support "push" (they are generated from global config).
"""

import json
import sys
from pathlib import Path

CONFIG_VERSION = 1

COMPONENTS = ["rules", "skills", "settings", "hooks"]

# Which directions are valid per component
VALID_DIRECTIONS = {
    "rules":    ["bidirectional", "push", "pull"],
    "skills":   ["bidirectional", "push", "pull"],
    "settings": ["push"],
    "hooks":    ["push"],
}

# Default config — current behavior
DEFAULT_CONFIG = {
    "version": CONFIG_VERSION,
    "mode": "default",
    "components": {
        "rules":    {"direction": "bidirectional", "enabled": True},
        "skills":   {"direction": "bidirectional", "enabled": True},
        "settings": {"direction": "push",          "enabled": True},
        "hooks":    {"direction": "push",           "enabled": True},
    },
}


class SyncConfig:
    """Loaded sync configuration with convenience accessors."""

    def __init__(self, data: dict):
        self._data = data

    @property
    def mode(self) -> str:
        return self._data.get("mode", "default")

    def component(self, name: str) -> dict:
        return self._data.get("components", {}).get(name, DEFAULT_CONFIG["components"][name])

    def direction(self, name: str) -> str:
        return self.component(name).get("direction", DEFAULT_CONFIG["components"][name]["direction"])

    def enabled(self, name: str) -> bool:
        return self.component(name).get("enabled", True)

    def to_dict(self) -> dict:
        return self._data


def load_config(config_dir: Path) -> SyncConfig:
    """Load sync_config.json, falling back to defaults."""
    path = config_dir / "sync_config.json"
    if path.exists():
        try:
            data = json.loads(path.read_text())
            # Merge with defaults so new keys are always present
            merged = json.loads(json.dumps(DEFAULT_CONFIG))
            if "mode" in data:
                merged["mode"] = data["mode"]
            for comp in COMPONENTS:
                if comp in data.get("components", {}):
                    merged["components"][comp].update(data["components"][comp])
            return SyncConfig(merged)
        except Exception:
            pass
    return SyncConfig(json.loads(json.dumps(DEFAULT_CONFIG)))


def save_config(config_dir: Path, cfg: SyncConfig):
    path = config_dir / "sync_config.json"
    path.write_text(json.dumps(cfg.to_dict(), indent=2) + "\n")


# ─── TUI Wizard ───────────────────────────────────────────────────────────────

BOX_W = 60

def _clear():
    print("\033[2J\033[H", end="")

def _header(title):
    print("┌" + "─" * (BOX_W - 2) + "┐")
    print("│" + f" {title}".ljust(BOX_W - 2) + "│")
    print("└" + "─" * (BOX_W - 2) + "┘")
    print()

def _section(title):
    print(f"\n  ── {title} " + "─" * max(0, BOX_W - 7 - len(title)))

def _ask(prompt, options: list[str], default: str) -> str:
    """Prompt user to pick from options. Returns chosen value."""
    default_idx = options.index(default) if default in options else 0
    print(f"\n  {prompt}")
    for i, opt in enumerate(options):
        marker = "●" if i == default_idx else "○"
        label = f" (default)" if i == default_idx else ""
        print(f"    [{i+1}] {marker} {opt}{label}")
    while True:
        try:
            raw = input(f"\n  Choice [1-{len(options)}] (Enter = {default}): ").strip()
            if raw == "":
                return default
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except (ValueError, KeyboardInterrupt, EOFError):
            pass
        print(f"  ✗ Enter a number 1–{len(options)}")

def _ask_bool(prompt: str, default: bool) -> bool:
    default_str = "y" if default else "n"
    while True:
        try:
            raw = input(f"\n  {prompt} [y/n] (Enter = {default_str}): ").strip().lower()
            if raw == "":
                return default
            if raw in ("y", "yes"):
                return True
            if raw in ("n", "no"):
                return False
        except (KeyboardInterrupt, EOFError):
            return default
        print("  ✗ Enter y or n")

def _confirm(data: dict) -> bool:
    print()
    _section("Review your config")
    print(f"  Mode: {data['mode']}")
    for comp, cfg in data["components"].items():
        status = "✓ enabled" if cfg["enabled"] else "✗ disabled"
        print(f"  {comp:10s}  {cfg['direction']:15s}  {status}")
    print()
    return _ask_bool("Save this configuration?", default=True)


def run_wizard(config_dir: Path, existing: SyncConfig | None = None) -> SyncConfig | None:
    """
    Interactive TUI wizard. Returns new SyncConfig or None if user cancelled.
    Existing config is used as defaults for each question.
    """
    _clear()
    _header("agent-sync  ·  Setup Wizard")

    print("  This wizard configures how agent-sync propagates your rules,")
    print("  skills, and settings across AI coding assistants.")
    print()
    print("  Press Ctrl+C at any time to cancel.\n")

    try:
        # ── Mode ──────────────────────────────────────────────────────────────
        _section("Sync Mode")
        print()
        print("  default       Rules/skills are bidirectional (newest wins).")
        print("                Settings/hooks push from global → repos.")
        print()
        print("  per_component Configure each component independently.")

        default_mode = existing.mode if existing else "default"
        mode = _ask("Choose mode:", ["default", "per_component"], default=default_mode)

        data = json.loads(json.dumps(DEFAULT_CONFIG))
        data["mode"] = mode

        if mode == "default":
            # Apply defaults silently — no further questions needed
            pass

        else:
            # ── Per-component ─────────────────────────────────────────────────
            for comp in COMPONENTS:
                _section(f"Component: {comp}")
                ex_comp = existing.component(comp) if existing else DEFAULT_CONFIG["components"][comp]

                enabled = _ask_bool(f"Enable {comp} sync?", default=ex_comp.get("enabled", True))
                data["components"][comp]["enabled"] = enabled

                if not enabled:
                    continue

                valid = VALID_DIRECTIONS[comp]
                if len(valid) == 1:
                    print(f"\n  Direction: {valid[0]}  (only option for {comp})")
                    data["components"][comp]["direction"] = valid[0]
                else:
                    print()
                    descs = {
                        "bidirectional": "newest version wins, syncs everywhere",
                        "push":          "master → agents only  (master = source of truth)",
                        "pull":          "agents → master only  (aggregate, don't push back)",
                    }
                    for d in valid:
                        print(f"    {d:15s}  {descs[d]}")
                    default_dir = ex_comp.get("direction", valid[0])
                    direction = _ask(f"Direction for {comp}:", valid, default=default_dir)
                    data["components"][comp]["direction"] = direction

        # ── Confirm ───────────────────────────────────────────────────────────
        cfg = SyncConfig(data)
        if _confirm(data):
            save_config(config_dir, cfg)
            print("\n  ✓ Configuration saved.\n")
            return cfg
        else:
            print("\n  Cancelled — no changes saved.\n")
            return None

    except KeyboardInterrupt:
        print("\n\n  Cancelled.\n")
        return None
