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
        assert "## Gemini Antigravity Specific" in content
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

def test_sync_creates_nonexistent_agent_files():
    """Test: Sync creates non-existent agent files with synced content."""
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

        # Create only Claude file with a shared rule
        claude_file.write_text("# Shared Rules\n- rule from claude\n## Claude Code Specific\n")
        
        # Cursor file does NOT exist yet
        assert not cursor_file.exists()

        # Initialize and sync
        sync._ensure_master_exists()
        sync.sync()

        # Cursor file should be created with synced content
        assert cursor_file.exists()
        
        cursor_content = cursor_file.read_text()
        assert "- rule from claude" in cursor_content
        assert "## Cursor Specific" in cursor_content


def test_legacy_cursorrules_merge_and_mirror(tmp_path, monkeypatch):
    """Legacy `.cursorrules` merges like Cursor; mirror matches global.mdc after sync."""
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / ".config" / "agent-rules-sync"
    config_dir.mkdir(parents=True)
    master = config_dir / "RULES.md"
    claude = tmp_path / ".claude" / "CLAUDE.md"
    cursor_mdc = tmp_path / ".cursor" / "rules" / "global.mdc"
    legacy = tmp_path / ".cursorrules"
    claude.parent.mkdir(parents=True)
    cursor_mdc.parent.mkdir(parents=True)

    legacy.write_text(
        "# Shared Rules\n- only in legacy cursorrules\n## Cursor Specific\n- cursor legacy bullet\n"
    )
    claude.write_text("# Shared Rules\n- from claude\n## Claude Code Specific\n")
    cursor_mdc.write_text("# Shared Rules\n- from claude\n## Cursor Specific\n")

    sync = AgentRulesSync()
    sync.config_dir = config_dir
    sync.master_file = master
    sync.agents = {
        "claude": {"name": "Claude Code", "path": claude, "description": ""},
        "cursor": {"name": "Cursor", "path": cursor_mdc, "description": ""},
    }

    sync._ensure_master_exists()
    sync.sync()

    master_text = master.read_text()
    assert "- only in legacy cursorrules" in master_text
    assert "- from claude" in master_text

    mirrored = legacy.read_text()
    assert "- only in legacy cursorrules" in mirrored
    assert "- from claude" in mirrored
    assert "## Cursor Specific" in mirrored
    assert "- cursor legacy bullet" in mirrored


def test_cursorrules_backup_slug_home_vs_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    sync = AgentRulesSync()
    home_cr = tmp_path / ".cursorrules"
    repo_cr = tmp_path / "myrepo" / ".cursorrules"
    assert sync._cursorrules_backup_slug(home_cr) == "cursorrules_home"
    assert sync._cursorrules_backup_slug(repo_cr) == "cursorrules_repo_myrepo"


def test_strip_cursor_rule_frontmatter():
    sync = AgentRulesSync()
    raw = "---\nalwaysApply: true\n---\n\n# Shared Rules\n- x\n"
    body = sync._strip_cursor_rule_frontmatter(raw)
    assert body.strip().startswith("# Shared Rules")
    assert "- x" in body
    plain = "# Shared Rules\n- y\n"
    assert sync._strip_cursor_rule_frontmatter(plain) == plain


def test_cursor_merge_multiple_rule_files_in_rules_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / ".config" / "agent-rules-sync"
    config_dir.mkdir(parents=True)
    master = config_dir / "RULES.md"
    rules = tmp_path / ".cursor" / "rules"
    rules.mkdir(parents=True)
    primary = rules / "global.mdc"
    extra = rules / "extra.md"
    claude = tmp_path / ".claude" / "CLAUDE.md"
    claude.parent.mkdir(parents=True)

    extra.write_text("# Shared Rules\n- from extra md\n## Cursor Specific\n- extra cur\n")
    primary.write_text("# Shared Rules\n- from claude\n- from primary\n## Cursor Specific\n")
    claude.write_text("# Shared Rules\n- from claude\n## Claude Code Specific\n")

    sync = AgentRulesSync()
    sync.config_dir = config_dir
    sync.master_file = master
    sync.agents = {
        "claude": {"name": "Claude Code", "path": claude, "description": ""},
        "cursor": {"name": "Cursor", "path": primary, "description": ""},
    }
    sync._ensure_master_exists()
    sync.sync()

    assert "- from extra md" in master.read_text()
    assert "- from primary" in master.read_text()
    merged = primary.read_text()
    assert "- from extra md" in merged
    assert "- from claude" in merged
    assert "- extra cur" in merged
    # User-owned extra.md is not overwritten; still has original content
    assert "from extra md" in extra.read_text()
