# Pre-Release Checklist for Agent Rules Sync v1.2.2

Use this checklist to verify everything is ready before external release.

---

## 📋 Code Quality

- [ ] All tests pass: `pytest tests/ -v`
- [ ] No syntax errors: `python -m py_compile agent_rules_sync.py install_daemon.py uninstall.py`
- [ ] Code style consistent (no obvious linting issues)
- [ ] No debug statements or print() statements left in code
- [ ] All docstrings present and accurate

---

## 🔍 Critical Fixes Verification

### Fix #1: Version Mismatch
- [ ] `setup.py` is minimal (only contains InstallWithDaemon class)
- [ ] Version only declared in `pyproject.toml`
- [ ] `setup.py` doesn't have duplicate `version = "1.0.0"` line
- [ ] Building from source produces version from pyproject.toml

### Fix #2: Windows Uninstall
- [ ] `uninstall.py` exists
- [ ] `uninstall.py` is pure Python (no bash dependencies)
- [ ] README.md has updated uninstall instructions
- [ ] Cross-platform uninstall tested (at least syntax check)

### Fix #3: Windows Persistence
- [ ] `install_daemon.py` has `_try_install_task_scheduler()` function
- [ ] Task Scheduler XML is well-formed
- [ ] Fallback to batch file is implemented
- [ ] Function returns True/False appropriately

### Fix #4: Graceful Shutdown
- [ ] `agent_rules_sync.py` has `self.stop_event` in `__init__`
- [ ] Windows daemon loop checks `while not self.stop_event.is_set():`
- [ ] `daemon_stop()` calls `self.stop_event.set()` on Windows
- [ ] No syntax errors in threading code

### Fix #5: Windows Tests
- [ ] `tests/test_windows_daemon.py` exists
- [ ] All Windows tests are syntactically valid
- [ ] Test file imports work without errors
- [ ] At least 10+ Windows-specific tests present

---

## 📦 Package Configuration

### pyproject.toml
- [ ] Version is set to `1.2.2`
- [ ] All required fields present
- [ ] Python version requirement correct (`>=3.8`)
- [ ] Console script entry point correct: `agent-rules-sync = "agent_rules_sync:main"`
- [ ] Description is accurate

### setup.py
- [ ] Only contains minimal custom install hook
- [ ] No version field in setup.py
- [ ] cmdclass includes InstallWithDaemon
- [ ] No duplicate metadata

### requirements.txt
- [ ] Still states "No external dependencies"
- [ ] Empty or only comments

---

## 📚 Documentation

### README.md
- [ ] Installation instructions are clear
- [ ] Windows installation mentions Task Scheduler
- [ ] Uninstall instructions updated for cross-platform
- [ ] Uninstall examples show `uninstall.py`
- [ ] Windows daemon commands section present
- [ ] All links are correct
- [ ] Examples are tested and accurate

### CHANGELOG.md
- [ ] v1.2.2 entry added
- [ ] Lists all 4 critical fixes
- [ ] Mentions Windows improvements
- [ ] Date is current

### Other Docs
- [ ] INSTALLATION.md is consistent with README
- [ ] CONTRIBUTING.md is still accurate
- [ ] QUICKSTART.md doesn't need updates

---

## 🧪 Testing

### Unit Tests
- [ ] `pytest tests/test_agent_rules_sync.py -v` passes
- [ ] All 8+ original tests pass
- [ ] No test failures or warnings

### Windows Tests
- [ ] `pytest tests/test_windows_daemon.py -v` passes
- [ ] All 13+ Windows tests run
- [ ] Tests use mocking appropriately (don't require Windows OS)

### Integration Tests
- [ ] `pytest tests/test_agent_rules_sync_integration.py -v` passes
- [ ] Full workflow tests still work

### Full Test Suite
- [ ] `pytest tests/ -v` passes completely
- [ ] Total test count is 30+
- [ ] No skipped tests (except platform-specific ones)
- [ ] No timeout failures

---

## 🔒 Security

- [ ] No hardcoded credentials or secrets
- [ ] No unsafe subprocess calls (all use properly escaped paths)
- [ ] File permissions are appropriate (0o644 for plist, etc.)
- [ ] No injection vulnerabilities
- [ ] User home directory used correctly (Path.home())

---

## 🚀 Build & Release

### Local Build Test
- [ ] `python -m build` completes without errors
- [ ] `dist/` directory contains `.tar.gz` and `.whl` files
- [ ] Wheel file has correct name with version 1.2.2
- [ ] Both distribution formats are valid

### Installation Test (Local)
- [ ] `pip install dist/agent_rules_sync-1.2.2-py3-none-any.whl` succeeds
- [ ] `agent-rules-sync --help` works
- [ ] `agent-rules-sync status` works
- [ ] Package installs to correct location
- [ ] Entry point command is available system-wide

### Cleanup
- [ ] `pip uninstall agent-rules-sync` works
- [ ] Daemon is properly stopped during uninstall
- [ ] No orphaned processes remain

---

## 🌐 Cross-Platform Verification

### Windows Compatibility (simulated)
- [ ] Code uses `pathlib.Path` (not hardcoded paths with `/`)
- [ ] No Unix-specific `os.fork()` on Windows path
- [ ] `sys.platform == "win32"` checks are correct
- [ ] Thread-based daemon for Windows is implemented
- [ ] Task Scheduler code is syntactically valid

### macOS Compatibility
- [ ] launchd plist is well-formed XML
- [ ] `launchctl` commands are correct
- [ ] Paths use `~/Library/LaunchAgents/` correctly

### Linux Compatibility
- [ ] systemd service file is valid
- [ ] `systemctl --user` commands are correct
- [ ] Paths use `~/.config/systemd/user/` correctly
- [ ] systemd availability check could be added (optional for v1.3)

---

## 📝 Git & Version Control

### Before Commit
- [ ] All changes are intentional (review git diff)
- [ ] No test artifacts or temp files committed
- [ ] No `.pyc` or `__pycache__` files
- [ ] `.gitignore` is up to date

### Commit
- [ ] Commit message is descriptive and clear
- [ ] Example: `fix: critical Windows/Linux compatibility and build system fixes (v1.2.2)`
- [ ] References the 4 critical issues in commit body

### Tag
- [ ] Tag name is `v1.2.2`
- [ ] Tag message includes summary of changes
- [ ] Tag is signed (optional but recommended)

### Push
- [ ] Changes pushed to main branch
- [ ] Tag pushed: `git push origin --tags`
- [ ] GitHub Actions (CI/CD) passes

---

## 🎯 Final Checks

- [ ] CHANGELOG.md mentions v1.2.2 is latest
- [ ] README.md doesn't reference old versions
- [ ] No "TODO" or "FIXME" comments in critical code
- [ ] No debug logging left enabled
- [ ] All file permissions are readable (644, not 600)
- [ ] Shebang lines are correct (`#!/usr/bin/env python3`)

---

## 📢 Release Notes Template

```markdown
# Release v1.2.2 - Critical Fixes for Windows & Linux

## Highlights
- ✅ Fixed version mismatch between setup.py and pyproject.toml
- ✅ Added cross-platform uninstall.py script (Windows-compatible)
- ✅ Upgraded Windows daemon persistence with Task Scheduler
- ✅ Implemented graceful shutdown for Windows daemon
- ✅ Added comprehensive Windows daemon tests

## Changes
- All changes are backward compatible
- No new external dependencies
- Pure Python, no shell scripts required for uninstall

## Windows Users
- Daemon now uses Windows Task Scheduler for reliable persistence
- Automatically restarts on system reboot
- Graceful stop with `agent-rules-sync stop` command

## Installation
```bash
pip install agent-rules-sync
```

## Uninstall
```bash
python uninstall.py
# OR
pip uninstall agent-rules-sync
```

See [README.md](https://github.com/dhruv-anand-aintech/agent-rules-sync/blob/main/README.md) for full documentation.

## Contributors
- @dhruv-anand-aintech (maintainer)
```

---

## ✅ Final Sign-Off

When all checks pass, you're ready to release:

```bash
# Verify everything one more time
pytest tests/ -v

# Build
python -m build

# Verify build
ls -lh dist/

# Tag and push
git tag v1.2.2
git push origin main --tags

# Publish to PyPI
python -m twine upload dist/*
```

---

**Status Before Release:** Complete this checklist and verify everything passes ✓

Once all items are checked, the project is ready for external sharing!
