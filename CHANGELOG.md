# Changelog

All notable changes to this project will be documented in this file.

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
