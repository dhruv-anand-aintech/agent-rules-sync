# Agent Rules Sync

**Synchronize your rules across Claude Code, Cursor, Gemini, and OpenCode in real-time.**

Edit rules in any AI agent → they automatically sync to all other agents.

## Installation

Works on **macOS**, **Linux**, and **Windows** (native + WSL).

### One-Line Install

```bash
pip install git+https://github.com/dhruv-anand-aintech/agent-rules-sync.git && agent-rules-sync
```

That's it! The daemon starts automatically and runs in the background.

### Platform-Specific Notes

**macOS & Linux:**
- Uses native fork-based daemon
- Logs to `~/.config/agent-rules-sync/daemon.log`

**Windows:**
- Uses background thread (no fork)
- Runs silently without console window
- Logs to `~/.config/agent-rules-sync/daemon.log`

## Usage

### 1. Start Auto-Sync (One Time)
```bash
agent-rules-sync
```

Runs in background, monitors all agent config files, syncs changes automatically.

### 2. Edit Rules Anywhere
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

### 3. Changes Sync Automatically
Within a few seconds, your changes appear in all other agents!

## How It Works

1. **Daemon monitors** all agent config files every 3 seconds
2. **Detects changes** in any file (master or agents)
3. **Merges rules** from all sources
4. **Syncs to all agents** automatically
5. **Deduplicates** identical rules

### No User Master File

The master rules file is stored hidden in `~/.config/agent-rules-sync/RULES.md` — you never need to touch it. Just edit your agent files!

## Commands

```bash
# Start daemon (runs in background)
agent-rules-sync

# Check sync status
agent-rules-sync status

# Watch mode (foreground, useful for debugging)
agent-rules-sync watch

# Stop daemon
agent-rules-sync stop
```

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
✓ **Automatic backups** — keeps timestamped backups
✓ **Fire and forget** — daemon runs in background
✓ **Zero config** — works out of the box
✓ **Real-time** — syncs within seconds

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
