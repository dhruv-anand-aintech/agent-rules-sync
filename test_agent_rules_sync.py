import tempfile
from pathlib import Path
from agent_rules_sync import AgentRulesSync

def test_extract_shared_rules():
    content = """# Shared Rules
- rule 1
- rule 2

## Claude Code Specific
- claude rule
"""
    sync = AgentRulesSync()
    rules = sync._extract_shared_rules(content)
    assert rules == {"- rule 1", "- rule 2"}

def test_extract_agent_rules():
    content = """# Shared Rules
- rule 1

## Claude Code Specific
- claude rule 1
- claude rule 2

## Cursor Specific
- cursor rule
"""
    sync = AgentRulesSync()
    rules = sync._extract_agent_rules(content, "claude")
    assert rules == {"- claude rule 1", "- claude rule 2"}

def test_extract_agent_rules_returns_empty():
    content = """# Shared Rules
- rule 1

## Cursor Specific
- cursor rule
"""
    sync = AgentRulesSync()
    rules = sync._extract_agent_rules(content, "claude")
    assert rules == set()

def test_build_file_content():
    sync = AgentRulesSync()
    shared = {"- rule 1", "- rule 2"}
    agent = {"- claude rule"}
    content = sync._build_file_content(shared, agent, "claude")
    
    assert "# Shared Rules" in content
    assert "- rule 1" in content
    assert "- rule 2" in content
    assert "## Claude Code Specific" in content
    assert "- claude rule" in content

def test_ensure_master_has_all_sections():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        master_file = config_dir / "RULES.md"

        sync = AgentRulesSync()
        sync.config_dir = config_dir
        sync.master_file = master_file

        # Create empty agent file
        agent_path = config_dir / "test_agent.md"
        agent_path.write_text("# Shared Rules\n- test rule\n")

        sync.agents["test"] = {"path": agent_path, "name": "Test", "description": ""}
        sync._ensure_master_exists()

        content = master_file.read_text()
        assert "# Shared Rules" in content
        assert "## Claude Code Specific" in content
        assert "## Cursor Specific" in content
        assert "## Gemini Specific" in content
        assert "## OpenCode Specific" in content

def test_sync_merges_shared_rules():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        master_file = config_dir / "RULES.md"
        claude_file = config_dir / "claude.md"
        cursor_file = config_dir / "cursor.md"

        sync = AgentRulesSync()
        sync.config_dir = config_dir
        sync.master_file = master_file

        # Setup agent files
        sync.agents["claude"]["path"] = claude_file
        sync.agents["cursor"]["path"] = cursor_file

        claude_file.write_text("# Shared Rules\n- rule from claude\n## Claude Code Specific\n")
        cursor_file.write_text("# Shared Rules\n- rule from cursor\n## Cursor Specific\n")

        sync._ensure_master_exists()
        sync.sync()

        master_content = master_file.read_text()
        # Both shared rules should be in master
        assert "- rule from claude" in master_content
        assert "- rule from cursor" in master_content

def test_sync_keeps_agent_specific_rules():
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

        claude_file.write_text("# Shared Rules\n## Claude Code Specific\n- claude only\n")
        cursor_file.write_text("# Shared Rules\n## Cursor Specific\n- cursor only\n")

        sync._ensure_master_exists()
        sync.sync()

        # Claude file should have its rule
        claude_content = claude_file.read_text()
        assert "- claude only" in claude_content

        # Cursor file should have its rule
        cursor_content = cursor_file.read_text()
        assert "- cursor only" in cursor_content

def test_sync_does_not_cross_pollinate_agent_rules():
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

        claude_file.write_text("# Shared Rules\n## Claude Code Specific\n- claude only\n")
        cursor_file.write_text("# Shared Rules\n## Cursor Specific\n- cursor only\n")

        sync._ensure_master_exists()
        sync.sync()

        # Claude file should NOT have cursor-specific rule
        claude_content = claude_file.read_text()
        assert "- cursor only" not in claude_content
        assert "## Cursor Specific" not in claude_content
