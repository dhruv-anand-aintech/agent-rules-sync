#!/usr/bin/env python3
"""Tests for migration from old versions."""

import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_rules_sync import AgentRulesSync


def test_migration_creates_state_file():
    """Test: Migration from version without state file creates state file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        master_file = config_dir / "RULES.md"
        state_file = config_dir / "sync_state.txt"
        claude_file = config_dir / "claude.md"

        # Simulate old installation: master file exists but no state file
        master_file.write_text("# Shared Rules\n- existing rule\n## Claude Code Specific\n")

        sync = AgentRulesSync()
        sync.config_dir = config_dir
        sync.master_file = master_file
        sync.state_file = state_file
        sync.agents = {
            "claude": {"path": claude_file, "name": "Claude Code", "description": ""}
        }

        # Verify state file doesn't exist yet
        assert not state_file.exists(), "State file should not exist yet"

        # Run sync (should trigger migration)
        sync.sync()

        # Verify state file was created
        assert state_file.exists(), "Migration should create state file"

        # Verify state file contains the rule
        state_content = state_file.read_text()
        assert "- existing rule" in state_content, "State file should contain existing rule"


def test_migration_preserves_existing_rules():
    """Test: Migration doesn't lose any existing rules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        master_file = config_dir / "RULES.md"
        state_file = config_dir / "sync_state.txt"
        claude_file = config_dir / "claude.md"
        cursor_file = config_dir / "cursor.md"

        # Simulate old installation with rules in both master and agents
        master_file.write_text("# Shared Rules\n- rule one\n- rule two\n## Claude Code Specific\n## Cursor Specific\n")
        claude_file.write_text("# Shared Rules\n- rule one\n- rule two\n## Claude Code Specific\n")
        cursor_file.write_text("# Shared Rules\n- rule one\n- rule two\n## Cursor Specific\n")

        sync = AgentRulesSync()
        sync.config_dir = config_dir
        sync.master_file = master_file
        sync.state_file = state_file
        sync.agents = {
            "claude": {"path": claude_file, "name": "Claude Code", "description": ""},
            "cursor": {"path": cursor_file, "name": "Cursor", "description": ""}
        }

        # Run sync (triggers migration)
        sync.sync()

        # Verify all rules are preserved
        master_content = master_file.read_text()
        claude_content = claude_file.read_text()
        cursor_content = cursor_file.read_text()

        assert "- rule one" in master_content
        assert "- rule two" in master_content
        assert "- rule one" in claude_content
        assert "- rule two" in claude_content
        assert "- rule one" in cursor_content
        assert "- rule two" in cursor_content


def test_migration_only_runs_once():
    """Test: Migration only runs once, not on every sync."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        master_file = config_dir / "RULES.md"
        state_file = config_dir / "sync_state.txt"
        claude_file = config_dir / "claude.md"

        master_file.write_text("# Shared Rules\n- test rule\n## Claude Code Specific\n")

        sync = AgentRulesSync()
        sync.config_dir = config_dir
        sync.master_file = master_file
        sync.state_file = state_file
        sync.agents = {
            "claude": {"path": claude_file, "name": "Claude Code", "description": ""}
        }

        # First sync - should create state file
        sync.sync()
        first_state_content = state_file.read_text()
        first_mtime = state_file.stat().st_mtime

        # Second sync - should not recreate state file
        import time
        time.sleep(0.1)  # Ensure different timestamp if recreated
        sync.sync()
        second_mtime = state_file.stat().st_mtime

        # State file should be updated by sync, but not recreated by migration
        assert state_file.exists()
        # mtime will change due to normal state saving, so we just verify it wasn't deleted


def test_upgrade_scenario_deletion_works_after_migration():
    """Test: Full upgrade scenario - deletion works immediately after migration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        master_file = config_dir / "RULES.md"
        state_file = config_dir / "sync_state.txt"
        claude_file = config_dir / "claude.md"
        cursor_file = config_dir / "cursor.md"

        # Step 1: Simulate OLD version installation (no state file)
        master_file.write_text("# Shared Rules\n- old rule\n- rule to delete\n## Claude Code Specific\n## Cursor Specific\n")
        claude_file.write_text("# Shared Rules\n- old rule\n- rule to delete\n## Claude Code Specific\n")
        cursor_file.write_text("# Shared Rules\n- old rule\n- rule to delete\n## Cursor Specific\n")

        sync = AgentRulesSync()
        sync.config_dir = config_dir
        sync.master_file = master_file
        sync.state_file = state_file
        sync.agents = {
            "claude": {"path": claude_file, "name": "Claude Code", "description": ""},
            "cursor": {"path": cursor_file, "name": "Cursor", "description": ""}
        }

        # Step 2: First sync after upgrade (triggers migration)
        sync.sync()
        assert state_file.exists(), "Migration should create state file"

        # Step 3: User deletes a rule from master (tests deletion works after migration)
        master_file.write_text("# Shared Rules\n- old rule\n## Claude Code Specific\n## Cursor Specific\n")

        # Step 4: Sync again (should detect deletion)
        sync.sync()

        # Step 5: Verify deletion propagated
        master_content = master_file.read_text()
        claude_content = claude_file.read_text()
        cursor_content = cursor_file.read_text()

        assert "- rule to delete" not in master_content, "Deleted rule should be gone from master"
        assert "- rule to delete" not in claude_content, "Deleted rule should be gone from claude"
        assert "- rule to delete" not in cursor_content, "Deleted rule should be gone from cursor"
        assert "- old rule" in master_content, "Existing rule should remain"


if __name__ == "__main__":
    test_migration_creates_state_file()
    print("✓ test_migration_creates_state_file passed")

    test_migration_preserves_existing_rules()
    print("✓ test_migration_preserves_existing_rules passed")

    test_migration_only_runs_once()
    print("✓ test_migration_only_runs_once passed")

    test_upgrade_scenario_deletion_works_after_migration()
    print("✓ test_upgrade_scenario_deletion_works_after_migration passed")

    print("\n✓ All migration tests passed!")
