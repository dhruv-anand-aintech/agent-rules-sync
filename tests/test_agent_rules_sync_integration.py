import tempfile
from pathlib import Path
from agent_rules_sync import AgentRulesSync

def test_full_workflow_shared_rules():
    """Test: Add shared rule in one agent, appears everywhere."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        master_file = config_dir / "RULES.md"
        claude_file = config_dir / "claude.md"
        cursor_file = config_dir / "cursor.md"

        sync = AgentRulesSync()
        sync.config_dir = config_dir
        sync.master_file = master_file
        sync.agents["claude"]["path"] = claude_file
        sync.agents["cursor"]["path"] = cursor_file

        # Initialize
        sync._ensure_master_exists()

        # User adds shared rule to claude
        claude_file.write_text("# Shared Rules\n- new shared rule\n## Claude Code Specific\n")

        # Sync
        sync.sync()

        # Check it appears in cursor
        cursor_content = cursor_file.read_text()
        assert "- new shared rule" in cursor_content

def test_full_workflow_agent_specific():
    """Test: Add agent-specific rule, doesn't appear in other agents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        master_file = config_dir / "RULES.md"
        claude_file = config_dir / "claude.md"
        cursor_file = config_dir / "cursor.md"

        sync = AgentRulesSync()
        sync.config_dir = config_dir
        sync.master_file = master_file
        # Override to only test claude and cursor
        sync.agents = {
            "claude": {"path": claude_file, "name": "Claude Code", "description": ""},
            "cursor": {"path": cursor_file, "name": "Cursor", "description": ""}
        }

        # Initialize
        sync._ensure_master_exists()

        # User adds claude-specific rule
        claude_file.write_text("# Shared Rules\n## Claude Code Specific\n- claude only rule\n")

        # Sync
        sync.sync()

        # Check it does NOT appear in cursor
        cursor_content = cursor_file.read_text()
        assert "- claude only rule" not in cursor_content
        assert "## Cursor Specific" in cursor_content

def test_full_workflow_rule_deletion():
    """Test: Delete rule from all sources, disappears from all agents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        master_file = config_dir / "RULES.md"
        claude_file = config_dir / "claude.md"
        cursor_file = config_dir / "cursor.md"

        sync = AgentRulesSync()
        sync.config_dir = config_dir
        sync.master_file = master_file
        # Override to only test claude and cursor
        sync.agents = {
            "claude": {"path": claude_file, "name": "Claude Code", "description": ""},
            "cursor": {"path": cursor_file, "name": "Cursor", "description": ""}
        }

        # Start with rule in both master and agents
        master_file.write_text("# Shared Rules\n- rule to delete\n## Claude Code Specific\n## Cursor Specific\n")
        claude_file.write_text("# Shared Rules\n- rule to delete\n## Claude Code Specific\n")
        cursor_file.write_text("# Shared Rules\n- rule to delete\n## Cursor Specific\n")

        # Delete from master AND agents
        master_file.write_text("# Shared Rules\n## Claude Code Specific\n## Cursor Specific\n")
        claude_file.write_text("# Shared Rules\n## Claude Code Specific\n")
        cursor_file.write_text("# Shared Rules\n## Cursor Specific\n")

        # Sync
        sync.sync()

        # Check it's gone from both
        claude_content = claude_file.read_text()
        cursor_content = cursor_file.read_text()
        assert "- rule to delete" not in claude_content
        assert "- rule to delete" not in cursor_content
