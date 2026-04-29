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

## Sync troubleshooting & recovery (field learnings)

These notes speed up diagnosing “sync is broken” reports. Several past incidents were **false alarms** or **recoverable from backups**.

### `status` shows everything “Out of sync” — often not a real failure
- `status()` compares **SHA256 of each agent file** to **SHA256 of the master `RULES.md`** (`agent_hash == master_hash`).
- Agent files are **not byte-identical** to the master by design: the master contains **every** `## … Specific` section; each agent file only has **shared rules + that agent’s section** (see `_build_file_content`).
- **Implication:** “Out of sync” in the UI does **not** mean propagation failed. Treat it as a **misleading heuristic** until the code compares **expected per-agent output** to **actual file** (or drops that check).
- **Verify sync:** Read `~/.claude/CLAUDE.md` / `~/.cursor/rules/global.mdc` and confirm shared bullets and the right agent section; do not rely on status alone.

### Only `-` bullet lines count under agent sections
- `_extract_agent_rules` only collects lines starting with `-` under `## {Agent} Specific`. Headings like `### Foo` and non-bullet text are **ignored** and will not round-trip through sync.
- **Fix for users:** Put agent-only guidance in **bullet** form (e.g. `- **Label:** description`).

### macOS LaunchAgent must point at a **stable** Python
- `install_daemon.py` bakes **`sys.executable`** into `~/Library/LaunchAgents/com.local.agent-rules-sync.plist`.
- If the package was installed from a **temporary** build/venv path, that path later disappears → **EX_CONFIG (exit 78)**, daemon never runs.
- **Fix:** `pip install -e .` (or `pip install agent-rules-sync`) using a **persistent** interpreter (e.g. miniforge `python3`), then re-run `install_daemon.py` (or reinstall) so the plist references that path. Confirm: `launchctl print gui/$(id -u)/com.local.agent-rules-sync` and that `Program` exists on disk.

### Union merge and “poison” shared rules
- Shared rules are the **union** of bullets from the **master** and **all** agent files. A stray bullet (e.g. `- new shared rule`) left in **any** file can remain in the merged set and **drown out** attention if other files were simplified.
- **Deletion detection** (`sync_state.txt`) removes a shared bullet only when it is absent from **every** relevant file per the current logic—misunderstandings here can look like “everything reverted to one line.”
- **Operational response:** Remove junk bullets from `RULES.md` and every agent file that still carries them, then `agent-sync sync rules` (or let the daemon pick it up).

### Fast recovery when the master or agents are clobbered
- **Backups:** `~/.config/agent-rules-sync/backups/` — look for `master_YYYYMMDD_HHMMSS.md` (and per-agent `claude_*.md`, `cursor_*.md`, etc.).
- **Pick a snapshot:** Prefer a **large** `master_*.md` (a few KB) with the full shared list and the agent sections you care about; filenames are timestamps (newer is not always better if a bad sync just ran).
- **Restore procedure:**
  1. Copy the chosen backup to `~/.config/agent-rules-sync/RULES.md` (or merge edits carefully).
  2. Run: `agent-sync sync rules` (or `python -m agent_rules_sync sync rules`) using the same environment you installed the package into.
  3. Spot-check `~/.claude/CLAUDE.md`, `~/.cursor/rules/global.mdc`, and `daemon.log`.
- **Editor trust:** If the UI still shows old content, confirm on disk with `head`/`wc`; some tools cache `~/.cursor/...` views.

### Development install
- From this repo: `pip install -e .` so `python -m agent_rules_sync` and the console scripts resolve `agent_sync_config` and friends; avoids `ModuleNotFoundError` when running the module from a random CWD.

### Legacy `.cursorrules` (Cursor)
- [Cursor rules docs](https://cursor.com/docs/rules): `.cursor/rules/` is preferred; **`.cursorrules`** at a project root is legacy but still supported.
- Sync **mirrors** the same body as `~/.cursor/rules/global.mdc` to **`~/.cursorrules`** and to **`<repo>/.cursorrules`** for each `repo_paths.json` entry, and **merges** bullets from those files on the next sync.

### Cursor: multiple files in `~/.cursor/rules/`
- When the primary path is `.../.cursor/rules/global.mdc`, sync **merges** all sibling `*.md` / `*.mdc` in that folder (recursive, skips `imported/`) and strips YAML **frontmatter** before parsing bullets.
- Only **`global.mdc`** is rewritten with the merged payload (plus `.cursorrules` mirrors); other rule files stay as you edited them (globs, `alwaysApply`, etc.).

## Configuration

### Agent Locations
Configured in `agent_rules_sync.py` (lines 43-52):
```python
self.agents = {
    "claude": {"path": Path.home() / ".claude/CLAUDE.md", ...},
    "cursor": {"path": Path.home() / ".cursor/rules/global.mdc", ...},
    # Legacy: ~/.cursorrules + <repo>/.cursorrules mirror global.mdc (see agent_rules_sync._cursorrules_legacy_paths)
    # ... etc
}
```

### Master Rules File
`~/.config/agent-rules-sync/RULES.md`

### Daemon Config
`~/.config/agent-rules-sync/` contains:
- `daemon.log` - Daemon activity log
- `daemon.pid` - Process ID file
- `sync_state.txt` - State tracking for deletion detection (auto-created)
- `backups/` - Automatic backups of all synced files

## Migration & Upgrades

### Upgrading from Old Versions
The package automatically migrates when upgrading:

**What happens on first sync after upgrade:**
1. Detects old installation (master file exists but no state file)
2. Creates `sync_state.txt` from current master file
3. Logs migration in `daemon.log`
4. No data loss - all existing rules are preserved

**Upgrade process:**
```bash
# Stop daemon
agent-rules-sync stop

# Upgrade package
pip install --upgrade agent-rules-sync

# Restart daemon (migration happens automatically on first sync)
agent-rules-sync daemon
```

**What's new in state-based deletion:**
- Deleting a rule from ANY file now propagates to all files
- Previous versions would add deleted rules back from other files
- State file tracks what existed before, enabling proper deletion detection

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

### Issue: State file missing after upgrade
- **Symptom**: Deletions not working after package upgrade
- **Solution**: State file is auto-created on first sync after upgrade
- **Verify**: Check for `~/.config/agent-rules-sync/sync_state.txt`
- **Manual fix**: Run `agent-rules-sync stop && agent-rules-sync daemon`
