import json
import pytest
from pathlib import Path
from agent_mcp_sync import AgentMcpSync

@pytest.fixture
def temp_home(tmp_path):
    """Setup a mock home directory structure."""
    home = tmp_path / "home"
    home.mkdir()
    
    # Mock global paths
    (home / ".cursor").mkdir()
    (home / ".gemini").mkdir()
    (home / ".config" / "opencode").mkdir(parents=True)

    # Library/Application Support for macOS mock
    (home / "Library" / "Application Support" / "Claude").mkdir(parents=True)
    
    return home

@pytest.fixture
def mcp_syncer(temp_home, monkeypatch):
    """Initialize AgentMcpSync with mock home and config dir."""
    monkeypatch.setattr(Path, "home", lambda: temp_home)
    
    config_dir = temp_home / ".config" / "agent-rules-sync"
    syncer = AgentMcpSync(config_dir=config_dir)
    return syncer

def test_mcp_sync_bidirectional(mcp_syncer, temp_home):
    # 1. Setup initial servers in different agents
    claude_code_path = temp_home / ".claude.json"
    claude_code_path.write_text(json.dumps({
        "mcpServers": {
            "claude-server": {"command": "claude-cmd"}
        }
    }))
    
    cursor_path = temp_home / ".cursor" / "mcp.json"
    cursor_path.write_text(json.dumps({
        "mcpServers": {
            "cursor-server": {"command": "cursor-cmd"}
        }
    }))
    
    # 2. Sync
    mcp_syncer.sync(direction="bidirectional")
    
    # 3. Verify master
    master_data = json.loads(mcp_syncer.master_file.read_text())
    assert "claude-server" in master_data["mcpServers"]
    assert "cursor-server" in master_data["mcpServers"]
    
    # 4. Verify propagation back to agents
    claude_data = json.loads(claude_code_path.read_text())
    assert "cursor-server" in claude_data["mcpServers"]
    
    cursor_data = json.loads(cursor_path.read_text())
    assert "claude-server" in cursor_data["mcpServers"]

def test_mcp_sync_with_repos(mcp_syncer, temp_home):
    # Setup repo
    repo = temp_home / "my-repo"
    repo.mkdir()
    repo_mcp = repo / ".mcp.json"
    repo_mcp.write_text(json.dumps({
        "mcpServers": {
            "repo-server": {"command": "repo-cmd"}
        }
    }))
    
    # Register repo
    repo_paths_file = mcp_syncer.config_dir / "repo_paths.json"
    repo_paths_file.write_text(json.dumps([str(repo)]))
    mcp_syncer._load_repo_paths()
    
    # Sync
    mcp_syncer.sync(direction="bidirectional")
    
    # Verify master has repo server
    master_data = json.loads(mcp_syncer.master_file.read_text())
    assert "repo-server" in master_data["mcpServers"]
    
    # Verify repo has been updated (if it was bidirectional)
    # Wait, my implementation only updates if it exists. It does exist.
    repo_data = json.loads(repo_mcp.read_text())
    assert "repo-server" in repo_data["mcpServers"]

def test_mcp_sync_preserves_other_keys(mcp_syncer, temp_home):
    # Setup Claude Code with extra keys
    claude_code_path = temp_home / ".claude.json"
    claude_code_path.write_text(json.dumps({
        "oauth": "secret-token",
        "mcpServers": {
            "s1": {"command": "c1"}
        }
    }))

    # Sync
    mcp_syncer.sync(direction="bidirectional")

    # Verify Claude Code still has OAuth
    claude_data = json.loads(claude_code_path.read_text())
    assert claude_data["oauth"] == "secret-token"
    assert "s1" in claude_data["mcpServers"]


def test_mcp_sync_opencode_bidirectional(mcp_syncer, temp_home):
    claude_code_path = temp_home / ".claude.json"
    claude_code_path.write_text(json.dumps({
        "mcpServers": {
            "html-portal": {"type": "stdio", "command": "tsx", "args": ["index.ts"]}
        }
    }))

    opencode_path = temp_home / ".config" / "opencode" / "opencode.json"
    opencode_path.write_text(json.dumps({
        "$schema": "https://opencode.ai/config.json",
        "permission": "allow",
        "mcp": {
            "context7": {"type": "remote", "url": "https://mcp.context7.com/mcp"}
        }
    }))

    mcp_syncer.sync(direction="bidirectional")

    master_data = json.loads(mcp_syncer.master_file.read_text())
    assert "html-portal" in master_data["mcpServers"]
    assert "context7" in master_data["mcpServers"]

    opencode_data = json.loads(opencode_path.read_text())
    assert "html-portal" in opencode_data["mcp"]
    assert opencode_data["mcp"]["html-portal"]["type"] == "stdio"
    assert "context7" in opencode_data["mcp"]
    assert "$schema" in opencode_data

    claude_data = json.loads(claude_code_path.read_text())
    assert "context7" in claude_data["mcpServers"]


def test_mcp_sync_opencode_preserves_top_level_keys(mcp_syncer, temp_home):
    opencode_path = temp_home / ".config" / "opencode" / "opencode.json"
    opencode_path.write_text(json.dumps({
        "$schema": "https://opencode.ai/config.json",
        "permission": "deny",
        "agent": {"general": {"model": "claude"}},
        "mcp": {}
    }))

    claude_code_path = temp_home / ".claude.json"
    claude_code_path.write_text(json.dumps({
        "mcpServers": {"s1": {"command": "c1"}}
    }))

    mcp_syncer.sync(direction="bidirectional")

    opencode_data = json.loads(opencode_path.read_text())
    assert opencode_data["$schema"] == "https://opencode.ai/config.json"
    assert opencode_data["permission"] == "deny"
    assert opencode_data["agent"] == {"general": {"model": "claude"}}
    assert "s1" in opencode_data["mcp"]
    assert opencode_data["mcp"]["s1"]["type"] == "stdio"


def test_mcp_sync_antigravity_cli_plugin(mcp_syncer, temp_home):
    claude_code_path = temp_home / ".claude.json"
    claude_code_path.write_text(json.dumps({
        "mcpServers": {"s1": {"command": "c1"}}
    }))

    mcp_syncer.sync(direction="bidirectional")

    plugin_dir = temp_home / ".gemini" / "antigravity-cli" / "plugins" / "agent-rules-sync"
    assert (plugin_dir / "plugin.json").exists()

    mcp_data = json.loads((plugin_dir / "mcp_config.json").read_text())
    assert "s1" in mcp_data["mcpServers"]
