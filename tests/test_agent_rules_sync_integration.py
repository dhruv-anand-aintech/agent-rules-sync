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

def test_full_workflow_creates_missing_agents():
    """Test: Sync creates missing agent files with synced content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        master_file = config_dir / "RULES.md"
        claude_file = config_dir / "claude.md"
        cursor_file = config_dir / "cursor.md"

        sync = AgentRulesSync()
        sync.config_dir = config_dir
        sync.master_file = master_file
        sync.agents = {
            "claude": {"path": claude_file, "name": "Claude Code", "description": ""},
            "cursor": {"path": cursor_file, "name": "Cursor", "description": ""}
        }

        # Initialize with only Claude file
        claude_file.write_text("# Shared Rules\n- shared rule\n## Claude Code Specific\n- claude specific\n")

        # Cursor doesn't exist
        assert not cursor_file.exists()

        # Sync
        sync._ensure_master_exists()
        sync.sync()

        # Cursor file should be created with synced content
        assert cursor_file.exists()
        cursor_content = cursor_file.read_text()
        assert "- shared rule" in cursor_content
        assert "## Cursor Specific" in cursor_content
        assert "- claude specific" not in cursor_content  # agent-specific rule stays in claude only

def test_daemon_watch_detects_master_file_changes():
    """Test: Watch mode detects changes to master file and syncs."""
    import time
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        master_file = config_dir / "RULES.md"
        claude_file = config_dir / "claude.md"
        cursor_file = config_dir / "cursor.md"

        sync = AgentRulesSync()
        sync.config_dir = config_dir
        sync.master_file = master_file
        sync.agents = {
            "claude": {"path": claude_file, "name": "Claude Code", "description": ""},
            "cursor": {"path": cursor_file, "name": "Cursor", "description": ""}
        }

        # Initialize
        sync._ensure_master_exists()
        sync.sync()

        # Get initial hash
        initial_master_hash = sync._get_file_hash(master_file)

        # Modify master file (add a test rule to the shared section)
        with open(master_file, 'r') as f:
            content = f.read()

        # Insert rule before the first agent-specific section
        modified_content = content.replace(
            "\n##",  # Before first agent section
            "\n- new test rule\n##",
            1
        )

        with open(master_file, 'w') as f:
            f.write(modified_content)

        # Sleep briefly to ensure file timestamp changes
        time.sleep(0.1)

        # Verify hash changed
        modified_master_hash = sync._get_file_hash(master_file)
        assert modified_master_hash != initial_master_hash, "Master file hash should change after edit"

        # Run sync (simulating daemon detecting change)
        sync.sync()

        # Verify the rule propagated to agent files
        claude_content = claude_file.read_text()
        cursor_content = cursor_file.read_text()

        assert "- new test rule" in claude_content, "New rule should appear in Claude file"
        assert "- new test rule" in cursor_content, "New rule should appear in Cursor file"

def test_daemon_watch_detects_agent_file_changes():
    """Test: Watch mode detects changes to agent files and updates master."""
    import time
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        master_file = config_dir / "RULES.md"
        claude_file = config_dir / "claude.md"
        cursor_file = config_dir / "cursor.md"

        sync = AgentRulesSync()
        sync.config_dir = config_dir
        sync.master_file = master_file
        sync.agents = {
            "claude": {"path": claude_file, "name": "Claude Code", "description": ""},
            "cursor": {"path": cursor_file, "name": "Cursor", "description": ""}
        }

        # Initialize
        sync._ensure_master_exists()
        sync.sync()

        # Modify Claude agent file (add shared rule)
        with open(claude_file, 'r') as f:
            claude_content = f.read()

        # Insert new shared rule before the agent-specific section
        modified_claude = claude_content.replace(
            "## Claude Code Specific",
            "- agent-added rule\n\n## Claude Code Specific"
        )

        with open(claude_file, 'w') as f:
            f.write(modified_claude)

        time.sleep(0.1)

        # Sync (simulate daemon)
        sync.sync()

        # Verify rule appears in master and other agents
        master_content = master_file.read_text()
        cursor_content = cursor_file.read_text()

        assert "- agent-added rule" in master_content, "Rule from agent should appear in master"
        assert "- agent-added rule" in cursor_content, "Rule from agent should propagate to other agents"
