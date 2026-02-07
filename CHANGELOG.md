# Changelog

All notable changes to this project will be documented in this file.

## [1.2.3] - 2026-02-07

### 🧪 Test Coverage Improvements

- **Added daemon watch detection tests** — Two new integration tests catch file watching regressions:
  - `test_daemon_watch_detects_master_file_changes`: Verifies master file changes are detected and synced to all agents
  - `test_daemon_watch_detects_agent_file_changes`: Verifies agent file changes are merged to master and synced to all agents
- Prevents breakage in the file hash-based change detection mechanism used by the daemon polling loop

## [1.2.2] - 2026-01-28

### 🔧 Critical Fixes (Windows & Linux Compatibility)

#### Build System
- **Fixed version mismatch** — Consolidated version management: single source of truth in `pyproject.toml` (removed duplicate version in `setup.py`)
- Simplified `setup.py` to minimal bootstrap code, keeping only custom `InstallWithDaemon` hook

#### Windows Daemon
- **Upgraded daemon persistence** — Now uses Windows Task Scheduler instead of unreliable startup folder batch files
  - Daemon survives system reboot (matches launchd/systemd behavior)
  - Auto-restarts if daemon crashes
  - Fallback to batch file if Task Scheduler unavailable
  - Implements proper graceful shutdown mechanism
- **Implemented graceful shutdown** — Windows daemon now responds to `agent-rules-sync stop` command
  - Added `threading.Event` for clean signal handling
  - Daemon exits within 3 seconds instead of hanging
  - No orphaned processes

#### Cross-Platform
- **Created `uninstall.py`** — Replaces bash-only `uninstall.sh`
  - Works natively on Windows, macOS, Linux
  - Pure Python (no shell dependencies)
  - Properly cleans up platform-specific artifacts
  - Preserves user's agent rule files

#### Testing
- **Added comprehensive Windows daemon tests** (13+ new tests)
  - Tests for daemon threading behavior
  - Task Scheduler installation verification
  - Graceful shutdown mechanism validation
  - Uninstall functionality coverage
  - Cross-platform compatibility checks

### 📚 Documentation
- Updated README.md with Windows Task Scheduler details
- Added Windows daemon management commands (schtasks examples)
- Updated uninstall instructions for cross-platform support
- Created pre-release checklist and implementation guides

### ✅ Quality
- All 26 tests pass (9 original + 4 integration + 13 Windows-specific)
- No external dependencies added (pure Python)
- Backward compatible (all changes preserve existing functionality)
- Cross-platform verified (pathlib.Path, sys.platform checks, proper path handling)

## [1.2.1] - 2026-01-28

### Added
- **Test coverage for file creation** — Verifies that non-existent agent config files are automatically created with synced content during sync
- Test case: `test_sync_creates_nonexistent_agent_files` ensures missing agent files are populated with shared rules
- Integration test: `test_full_workflow_creates_missing_agents` validates full workflow with missing agents

### Fixed
- Test suite organization — Moved to `tests/` directory with proper pytest structure

## [1.2.0] - 2026-01-28

### Added
- **5 new agent configuration locations** for broader compatibility:
  - `~/.config/agents/AGENTS.md` (Config Agents)
  - `~/.codex/AGENTS.md` (Codex)
  - `~/.config/AGENTS.md` (Config root)
  - `~/.agent/AGENTS.md` (Local Agent)
  - `~/.agent/AGENT.md` (Local Agent alternate)
- All 9 agent locations now automatically synced
- Updated README with all supported locations

## [1.1.1] - 2026-01-28

### Fixed
- Uninstall script now reliably kills daemon process using pkill fallback
- Prevents orphaned daemon processes after uninstall

## [1.1.0] - 2026-01-28

### Added
- **Agent-Specific Rules** — Rules under `## [Agent] Specific` sections stay local and don't sync to other agents
- **Rule Deletion** — Simply delete rules and they disappear from all agents on next sync
- **Structured Master File** — Master file now organized with "Shared Rules" + agent-specific sections
- Comprehensive test suite (11 tests: 8 unit + 3 integration)
- Detailed documentation for new rule management features

### Changed
- Master file format updated from flat list to structured sections
- Improved sync algorithm to handle shared vs agent-specific rules separately
- Better merge behavior: shared rules sync everywhere, agent-specific stays local

### Technical
- New parser methods for extracting shared/agent-specific rules
- Rewritten sync algorithm with 4-step process
- All tests passing with 100% coverage of new features

## [1.0.0] - 2026-01-25

### Added
- Initial public release
- Cross-platform daemon support (macOS, Linux, Windows)
- Automatic rule synchronization across AI coding assistants
- Smart merge algorithm with deduplication
- Status monitoring command
- Watch/foreground mode for debugging
- One-line install and uninstall
- Support for:
  - Claude Code (`~/.claude/CLAUDE.md`)
  - Cursor (`~/.cursor/rules/global.mdc`)
  - Gemini Antigravity (`~/.gemini/GEMINI.md`)
  - OpenCode (`~/.config/opencode/AGENTS.md`)

### Features
- ✓ Bidirectional sync (any file can be source of truth)
- ✓ Automatic deduplication of rules
- ✓ Timestamped backups before changes
- ✓ Hidden master file in `~/.config/agent-rules-sync/`
- ✓ Zero configuration needed
- ✓ Real-time file monitoring
- ✓ Daemon logs for debugging
