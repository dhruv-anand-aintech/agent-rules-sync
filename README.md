# Agent Rules Sync

**Synchronize your rules across Claude Code, Cursor, Gemini, and OpenCode in real-time.**

Edit rules in any AI agent → they automatically sync to all other agents.

## Installation

Works on **macOS**, **Linux**, and **Windows** (native + WSL).

### One-Line Install

```bash
pip install git+https://github.com/dhruv-anand-aintech/agent-rules-sync.git
```

**That's it!** The daemon installs and starts automatically.

### What Happens During Installation

1. **Daemon is installed** as a system service (auto-starts on boot)
2. **Service starts immediately** and runs in the background
3. **Rules sync automatically** every 3 seconds

### Platform-Specific Installation

**macOS:**
- Installs as launchd service (`com.local.agent-rules-sync`)
- Auto-starts on login
- Logs to `~/.config/agent-rules-sync/`
- File: `~/Library/LaunchAgents/com.local.agent-rules-sync.plist`

**Linux:**
- Installs as systemd user service (`agent-rules-sync.service`)
- Auto-starts on login
- Logs to `~/.config/agent-rules-sync/daemon.log`
- File: `~/.config/systemd/user/agent-rules-sync.service`

**Windows:**
- Installs batch file to startup folder
- Auto-starts on next login
- Logs to `~/.config/agent-rules-sync/`
- File: `~/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/agent-rules-sync.bat`

## Usage

### The daemon is already running!

After installation, the daemon runs automatically in the background. Just start editing.

### 1. Edit Rules Anywhere
Pick any location and edit:
```bash
# Edit Claude Code rules
nano ~/.claude/CLAUDE.md

# Edit Cursor rules
nano ~/.cursor/rules/global.mdc

# Edit Gemini rules
nano ~/.gemini/GEMINI.md

# Edit OpenCode rules
nano ~/.config/opencode/AGENTS.md
```

Just add or remove lines starting with `-`:
```markdown
- rule 1
- rule 2
- rule 3
```

### 2. Changes Sync Automatically
Within 3 seconds, your changes appear in all other agents! No manual sync needed.

## How It Works

1. **Daemon monitors** all agent config files every 3 seconds
2. **Detects changes** in any file (master or agents)
3. **Merges rules** from all sources
4. **Syncs to all agents** automatically
5. **Deduplicates** identical rules

### No User Master File

The master rules file is stored hidden in `~/.config/agent-rules-sync/RULES.md` — you never need to touch it. Just edit your agent files!

## Commands

The daemon runs automatically. These commands are for management:

```bash
# Check daemon status
agent-rules-sync status

# Watch mode (foreground, useful for debugging)
agent-rules-sync watch

# Stop daemon (it will auto-restart on next login)
agent-rules-sync stop
```

## Backups

**Every file change is automatically backed up** with a timestamp.

View your backups:
```bash
ls -lah ~/.config/agent-rules-sync/backups/
```

Restore a previous version:
```bash
cp ~/.config/agent-rules-sync/backups/claude_20260125_014532.md ~/.claude/CLAUDE.md
```

For detailed backup information, see [BACKUPS.md](BACKUPS.md)

To completely uninstall:
```bash
curl -fsSL https://raw.githubusercontent.com/dhruv-anand-aintech/agent-rules-sync/main/uninstall.sh | bash
```

## When Changes Take Effect

**Important:** Different agents load configuration at different times. After Agent Rules Sync updates files, you may need to restart your agent for changes to take effect:

| Agent | What to Do |
|-------|-----------|
| **Claude Code** | Restart the application or start a new session |
| **Cursor** | Changes apply automatically in new conversations |
| **Gemini Antigravity** | Run `/memory refresh` command or restart |
| **OpenCode** | Restart or start a new session |

For detailed technical information, see [AGENT_FILE_RELOAD.md](AGENT_FILE_RELOAD.md)

## Example Workflow

**Terminal 1:**
```bash
$ agent-rules-sync
Starting Agent Rules Sync daemon...
✓ Daemon started (PID: 12345)
```

**Terminal 2:**
```bash
$ echo "- use pydantic for validation" >> ~/.claude/CLAUDE.md
```

**Within 3 seconds, the rule appears in:**
- `~/.cursor/rules/global.mdc`
- `~/.gemini/GEMINI.md`
- `~/.config/opencode/AGENTS.md`

✓ Done! No manual sync needed.

## Features

✓ **Bidirectional sync** — rules can be added anywhere
✓ **Auto-deduplication** — same rule doesn't appear twice
✓ **Automatic backups** — timestamped backups before every change
✓ **Fire and forget** — daemon auto-starts and runs in background
✓ **Zero config** — works out of the box
✓ **Real-time** — syncs within 3 seconds
✓ **Safe recovery** — restore any previous version from backups

## Merging Behavior

Rules are **merged**, not replaced. If you have:

**Master:** `- rule A`, `- rule B`
**Claude:** `- rule A`, `- rule B`, `- rule C`

After sync, all agents get: `- rule A`, `- rule B`, `- rule C`

No rules are lost!

## Architecture

```
Your edits in any agent file
         ↓
    Daemon detects change
         ↓
    Merge all rules
         ↓
    Update all agents
         ↓
    Done! (rules synced everywhere)
```

## Monitoring

Check status anytime:
```bash
$ agent-rules-sync status

======================================================================
Agent Rules Sync Status
======================================================================

📂 Config directory: ~/.config/agent-rules-sync

📄 Master Rules: ~/.config/agent-rules-sync/RULES.md
   Hash: acfa47839976...

🤖 Claude Code
   Path: ~/.claude/CLAUDE.md
   Status: ✓ In sync

🤖 Cursor
   Path: ~/.cursor/rules/global.mdc
   Status: ✓ In sync

🤖 Gemini Antigravity
   Path: ~/.gemini/GEMINI.md
   Status: ✓ In sync

🤖 OpenCode
   Path: ~/.config/opencode/AGENTS.md
   Status: ✓ In sync

======================================================================
```

## Logs

Daemon logs are stored in:
```
~/.config/agent-rules-sync/daemon.log
```

View recent activity:
```bash
tail -f ~/.config/agent-rules-sync/daemon.log
```

## Troubleshooting

### Daemon not syncing?
```bash
# Check status
agent-rules-sync status

# Check logs
tail ~/.config/agent-rules-sync/daemon.log

# Restart
agent-rules-sync stop
agent-rules-sync  # Start again
```

### Want to debug in foreground?
```bash
# Run in foreground instead of daemon
agent-rules-sync watch
```

### Need to see what's backed up?
```bash
ls -la ~/.config/agent-rules-sync/backups/
```

### How do I uninstall?

**One-liner:**
```bash
curl -fsSL https://raw.githubusercontent.com/dhruv-anand-aintech/agent-rules-sync/main/uninstall.sh | bash
```

Or manually:
```bash
agent-rules-sync stop                    # Stop daemon
pip uninstall -y agent-rules-sync        # Remove package
rm -rf ~/.config/agent-rules-sync        # Clean up config
```

Your agent rule files are preserved and not deleted!

## Requirements

- Python 3.8+
- Claude Code, Cursor, Gemini, or OpenCode installed (at least one)

## License

MIT License - see LICENSE file

## Contributing

Contributions welcome! Feel free to submit issues and pull requests.

## Support

- 🐛 Found a bug? [Open an issue](https://github.com/dhruv-anand-aintech/agent-rules-sync/issues)
- 💡 Have a feature idea? [Start a discussion](https://github.com/dhruv-anand-aintech/agent-rules-sync/discussions)
- ❓ Questions? Check existing issues or create a new one

## Repository

https://github.com/dhruv-anand-aintech/agent-rules-sync

---

**Keep your AI agent rules in sync. Edit anywhere. Sync everywhere.**
