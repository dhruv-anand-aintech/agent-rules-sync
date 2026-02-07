# Agent Rules Sync - Project Context

## Quick Facts
- **Project**: Agent Rules Sync - Synchronize rules across AI coding assistants
- **Language**: Python 3.8+
- **Main File**: `agent_rules_sync.py` (single-file module with daemon support)
- **Tests**: Located in `tests/` directory (29 tests, all passing)
- **Package**: Published on PyPI - https://pypi.org/project/agent-rules-sync/

## Release Workflow

### 1. Prepare Changes
- Make code changes and commit to git
- Run tests: `/usr/bin/python3 -m pytest tests/ -v`
- Ensure all tests pass before releasing

### 2. Version Bump
Update THREE files to bump version (e.g., from 1.2.2 to 1.2.3):

**File 1: `pyproject.toml`** (line 7)
```toml
version = "1.2.3"
```

**File 2: `CHANGELOG.md`** (add entry at top)
```markdown
## [1.2.3] - 2026-02-07

### 🧪 Category Name
- Feature description 1
- Feature description 2
```

**File 3: `setup.py`** - NO CHANGE NEEDED
- It reads version from `pyproject.toml` automatically

**Commit the version bump:**
```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 1.2.3 with [description]"
git push origin main
```

### 3. Build Package
```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info

# Build wheel and sdist using miniforge python
python3.10 -m build
```

Output: `dist/agent_rules_sync-1.2.3.tar.gz` and `dist/agent_rules_sync-1.2.3-py3-none-any.whl`

### 4. Publish to PyPI
```bash
# Upgrade twine if needed
python3.10 -m pip install --upgrade twine

# Upload to PyPI (uses ~/.pypirc credentials)
python3.10 -m twine upload dist/agent_rules_sync-1.2.3* --skip-existing
```

Verify at: https://pypi.org/project/agent-rules-sync/

### 5. Create GitHub Release
```bash
# Create and push git tag
git tag -a v1.2.3 -m "test: add daemon watch detection tests"
git push origin v1.2.3

# Create GitHub release (with auto-generated notes)
gh release create v1.2.3 --title "v1.2.3: Test Coverage Improvements" --notes "Release notes here"
```

Verify at: https://github.com/dhruv-anand-aintech/agent-rules-sync/releases

## Key Commands Reference

### Testing
```bash
# Run all tests
/usr/bin/python3 -m pytest tests/ -v

# Run specific test
/usr/bin/python3 -m pytest tests/test_agent_rules_sync_integration.py::test_daemon_watch_detects_master_file_changes -v
```

### Local Development
```bash
# Install in editable mode (picks up code changes immediately)
pip install -e .

# Check daemon status
agent-rules-sync status

# Stop daemon
agent-rules-sync stop

# Run in watch mode (for debugging)
agent-rules-sync watch
```

### Build System Notes
- **Single source of truth**: Version is defined ONLY in `pyproject.toml`
- **setup.py**: Minimal bootstrap file with `InstallWithDaemon` hook
- **No duplication**: setup.py reads metadata from pyproject.toml via setuptools
- **Python version**: Use `python3.10` from miniforge for consistent builds

## Architecture Notes

### File Structure
```
agent_rules_sync.py          # Main module with AgentRulesSync class
install_daemon.py            # Auto-installer for daemon (runs after pip install)
setup.py                     # Custom install hook
pyproject.toml               # Package metadata & build config
tests/
  ├── test_agent_rules_sync.py           # Unit tests
  ├── test_agent_rules_sync_integration.py # Integration tests (includes watch tests)
  └── test_windows_daemon.py             # Windows-specific tests
```

### Key Classes & Methods
- **AgentRulesSync**: Main sync engine
  - `sync()`: Merge rules from all agents to master and back
  - `watch()`: Poll for file changes every 3 seconds (used by daemon)
  - `status()`: Display sync status and daemon info
  - `daemon_start()`: Start background daemon (platform-aware)

### Sync Logic
1. Read master file and extract shared/agent-specific sections
2. Merge rules from all agent files into master
3. Rebuild master with all sections in sorted order
4. Write synced content to each agent file (shared + their section only)
5. Log all backups and changes

## Test Coverage

### Integration Tests
- ✅ `test_daemon_watch_detects_master_file_changes`: Master→agents sync
- ✅ `test_daemon_watch_detects_agent_file_changes`: Agents→master→agents sync
- ✅ Full workflow tests for shared & agent-specific rules
- ✅ Rule deletion and merging tests

### Unit Tests
- ✅ Rule extraction (shared vs agent-specific)
- ✅ File content building
- ✅ Master file initialization

### Daemon Tests
- ✅ Windows daemon threading
- ✅ Task Scheduler installation
- ✅ Graceful shutdown
- ✅ PID file management

## Debugging Tips

### Daemon not syncing?
1. Check status: `agent-rules-sync status`
2. Check logs: `tail -50 ~/.config/agent-rules-sync/daemon.log`
3. Restart: `agent-rules-sync stop && agent-rules-sync daemon`
4. Test manually: `python3 agent_rules_sync.py watch`

### File changes not detected?
- Daemon polls every 3 seconds (check logs for timestamps)
- File hash comparison is case-sensitive
- Ensure file is in proper section (shared or agent-specific)

### Build issues?
- Use `python3.10` from miniforge (not system python)
- Clear cache: `rm -rf dist/ build/ *.egg-info __pycache__`
- Check setuptools: `python3.10 -m pip install --upgrade setuptools wheel`

## Configuration

### Agent Locations
Configured in `agent_rules_sync.py` (lines 43-52):
```python
self.agents = {
    "claude": {"path": Path.home() / ".claude/CLAUDE.md", ...},
    "cursor": {"path": Path.home() / ".cursor/rules/global.mdc", ...},
    # ... etc
}
```

### Master Rules File
`~/.config/agent-rules-sync/RULES.md`

### Daemon Config
`~/.config/agent-rules-sync/` (daemon.log, daemon.pid, backups/)

## Common Issues & Solutions

### Issue: PyPI upload fails with "Metadata is missing required fields"
- **Solution**: Upgrade twine: `python3.10 -m pip install --upgrade twine`
- Older versions don't support Metadata-Version 2.4

### Issue: "No such file or directory" when running tests
- **Solution**: Use full python path: `/usr/bin/python3 -m pytest ...`
- Don't use venv python as it doesn't have pytest

### Issue: Daemon stops after reboot (macOS)
- **Solution**: launchd plist installed at startup, should auto-restart
- Check: `launchctl list | grep agent-rules-sync`
