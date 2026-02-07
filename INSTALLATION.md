# Installation & Setup Guide

## What Happens During Installation

The Agent Rules Sync installation is designed to be **set-it-and-forget-it**:

### One-Command Installation

**From PyPI (recommended):**
```bash
pip install agent-rules-sync
```

**From source:**
```bash
pip install git+https://github.com/dhruv-anand-aintech/agent-rules-sync.git
```

**Using uv (faster):**
```bash
uv pip install agent-rules-sync
```

### During Installation

1. **Python package installed** to site-packages
2. **`agent-rules-sync` command** becomes available system-wide
3. **System service installed** (platform-specific)
4. **Daemon starts automatically** and runs in background
5. **Auto-restarts on system boot** (persists across reboots)

### After Installation

The daemon is **already running**. You can:
- Edit any agent config file immediately
- Changes sync within 3 seconds
- Daemon continues running until explicitly stopped

---

## Platform-Specific Installation Details

### macOS

**Service Type:** launchd (Apple's init system)

**Installation:**
```
Installs: ~/Library/LaunchAgents/com.local.agent-rules-sync.plist
Starts automatically: On login
Logs to: ~/.config/agent-rules-sync/daemon.log
```

**Check status:**
```bash
launchctl list | grep agent-rules-sync
```

**Manual start/stop:**
```bash
# Start manually
launchctl load ~/Library/LaunchAgents/com.local.agent-rules-sync.plist

# Stop manually
launchctl unload ~/Library/LaunchAgents/com.local.agent-rules-sync.plist
```

### Linux (systemd)

**Service Type:** systemd user service

**Installation:**
```
Installs: ~/.config/systemd/user/agent-rules-sync.service
Starts automatically: On login
Logs to: ~/.config/agent-rules-sync/daemon.log
```

**Check status:**
```bash
systemctl --user status agent-rules-sync
```

**Manual control:**
```bash
# Check status
systemctl --user status agent-rules-sync

# Start manually
systemctl --user start agent-rules-sync

# Stop manually
systemctl --user stop agent-rules-sync

# View logs
journalctl --user -u agent-rules-sync -f
```

### Windows

**Service Type:** Batch file in startup folder

**Installation:**
```
Installs: %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\agent-rules-sync.bat
Starts automatically: On next login
Logs to: ~/.config/agent-rules-sync/daemon.log
```

**Manual start:**
```bash
python -m agent_rules_sync
```

---

## Troubleshooting Installation

### Daemon didn't start automatically

**Check if it's running:**
```bash
agent-rules-sync status
```

**Try to start manually:**
```bash
agent-rules-sync
```

**Check logs:**
```bash
tail ~/.config/agent-rules-sync/daemon.log
```

### Python 3.8+ required

Ensure you have Python 3.8 or higher:
```bash
python3 --version
```

If using an older Python, install a newer version first.

### Permission issues on Linux

If you get permission errors during installation:
```bash
# Install for user only (recommended)
pip install --user git+https://github.com/dhruv-anand-aintech/agent-rules-sync.git

# Or use sudo (not recommended)
sudo pip install git+https://github.com/dhruv-anand-aintech/agent-rules-sync.git
```

### Service failed to install on macOS

If launchctl load fails, try manually:
```bash
cd ~/.config/agent-rules-sync
/usr/bin/python3 -m agent_rules_sync
```

---

## Uninstalling

### One-Command Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/dhruv-anand-aintech/agent-rules-sync/main/uninstall.sh | bash
```

### What Gets Uninstalled

- ✓ Daemon service (launchd/systemd/batch file)
- ✓ Python package
- ✓ Configuration directory
- ✓ **Preserves:** Your agent rule files (unchanged)

### Manual Uninstall

**macOS:**
```bash
launchctl unload ~/Library/LaunchAgents/com.local.agent-rules-sync.plist
rm ~/Library/LaunchAgents/com.local.agent-rules-sync.plist
pip uninstall agent-rules-sync
rm -rf ~/.config/agent-rules-sync
```

**Linux:**
```bash
systemctl --user stop agent-rules-sync
systemctl --user disable agent-rules-sync
systemctl --user daemon-reload
pip uninstall agent-rules-sync
rm -rf ~/.config/agent-rules-sync
```

**Windows:**
```bash
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\agent-rules-sync.bat"
pip uninstall agent-rules-sync
rmdir "%USERPROFILE%\.config\agent-rules-sync"
```

---

## Daemon Lifecycle

### Startup Sequence

1. **System boots** → loads service definition
2. **Service auto-starts** when you log in
3. **Daemon initializes** config directories
4. **Monitoring begins** - watches all agent files
5. **Ready to sync** - any file changes trigger sync

### During Execution

- Checks for file changes **every 3 seconds**
- Merges rules from all sources
- Syncs to all agent files
- Logs activity to `daemon.log`
- Continues running in background

### Graceful Shutdown

```bash
# Daemon will:
agent-rules-sync stop

# 1. Stop monitoring
# 2. Save state
# 3. Clean up resources
# 4. Exit cleanly
```

### Auto-Restart (if killed)

**macOS:** launchd restarts daemon automatically if killed
**Linux:** systemd restarts daemon automatically if killed
**Windows:** Daemon is thread-based and will restart on next login

---

## Configuration Files

After installation, these files are created:

```
~/.config/agent-rules-sync/
├── RULES.md              # Master rules (hidden from user)
├── daemon.pid            # Process ID
├── daemon.log            # Activity logs
└── backups/              # Timestamped backups
    ├── claude_*.md
    ├── cursor_*.md
    ├── gemini_*.md
    └── opencode_*.md
```

Plus platform-specific service files:
- **macOS:** `~/Library/LaunchAgents/com.local.agent-rules-sync.plist`
- **Linux:** `~/.config/systemd/user/agent-rules-sync.service`
- **Windows:** `%APPDATA%/Microsoft/Windows/Start Menu/Programs/Startup/agent-rules-sync.bat`

---

## Managing the Daemon

### Commands

```bash
# Check if daemon is running and status
agent-rules-sync status

# Watch in foreground (for debugging)
agent-rules-sync watch

# Stop daemon (won't start again until reboot/login)
agent-rules-sync stop

# View logs
tail ~/.config/agent-rules-sync/daemon.log
tail -f ~/.config/agent-rules-sync/daemon.log  # Follow logs

# Check backups
ls ~/.config/agent-rules-sync/backups/
```

### Debugging

If sync isn't working:

1. **Check daemon is running:**
   ```bash
   agent-rules-sync status
   ```

2. **Check logs for errors:**
   ```bash
   tail -20 ~/.config/agent-rules-sync/daemon.log
   ```

3. **Try watch mode:**
   ```bash
   agent-rules-sync watch
   ```

4. **Restart daemon:**
   ```bash
   agent-rules-sync stop
   # Wait for 5 seconds, then:
   # On next activity, daemon auto-restarts
   ```

---

## Getting Help

- **GitHub Issues:** https://github.com/dhruv-anand-aintech/agent-rules-sync/issues
- **Daemon Logs:** `~/.config/agent-rules-sync/daemon.log`
- **Service Status:** `agent-rules-sync status`

---

**Installation complete!** The daemon is now running and will continue to sync your rules automatically.
