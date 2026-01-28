# Changelog

All notable changes to this project will be documented in this file.

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
