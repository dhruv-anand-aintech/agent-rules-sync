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
