# Agent Rules Sync

**Synchronize your rules and skills across Claude Code, Cursor, Gemini, OpenCode, and Codex in real-time.**

Edit rules or skills in any AI agent → they automatically sync to all other agents.

## Installation

Works on **macOS**, **Linux**, and **Windows** (native + WSL).

### Quick Install

**Using pip:**
```bash
pip install agent-rules-sync
```

**Using uv (faster):**
```bash
uv pip install agent-rules-sync
```

**That's it!** The daemon installs and starts automatically.

### What Happens During Installation

1. **Daemon is installed** as a system service (auto-starts on boot)
2. **Service starts immediately** and runs in the background
3. **Rules and skills sync automatically** every 3 seconds

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
- Installs via Windows Task Scheduler (with startup folder fallback)
- Auto-starts on user login
- Logs to `~/.config/agent-rules-sync/daemon.log`
- Task name: `agent-rules-sync` (visible in Task Scheduler)
- View logs: `type %USERPROFILE%\.config\agent-rules-sync\daemon.log`

## Usage

### The daemon is already running!

After installation, the daemon runs automatically in the background. Just start editing.

### Shared vs Agent-Specific Rules

Rules can be **shared** (sync to all agents) or **agent-specific** (stay local to one agent).

**Shared Rules** sync to all agents automatically:
```markdown
# Shared Rules
- use pydantic for validation  <- Appears in all agents
- always test edge cases
```

**Agent-Specific Rules** stay local and don't sync to other agents:
```markdown
# Shared Rules
- shared rule

## Claude Code Specific
- use claude-specific syntax  <- Only in Claude Code, doesn't sync elsewhere
```

Each agent file has the same structure:
```markdown
# Shared Rules
- rule 1 (syncs everywhere)
- rule 2

## Claude Code Specific
- claude local rule

## Cursor Specific
- cursor local rule
```

**Removing Rules** is simple - just delete the line from any agent file or the master, and it disappears on the next sync (backups preserve deleted rules).

### 1. Edit Rules Anywhere
Pick any location and edit:
```bash
# Main AI Editors
vim ~/.claude/CLAUDE.md          # Claude Code
vim ~/.cursor/rules/global.mdc   # Cursor
vim ~/.gemini/GEMINI.md          # Gemini Antigravity
vim ~/.config/opencode/AGENTS.md # OpenCode

# Additional Agent Locations
vim ~/.config/agents/AGENTS.md   # Config Agents
vim ~/.codex/AGENTS.md           # Codex
vim ~/.config/AGENTS.md          # Config root
vim ~/.agent/AGENTS.md           # Local Agent
vim ~/.agent/AGENT.md            # Local Agent (alternate)
```

Just add or remove lines starting with `-`:
```markdown
- rule 1
- rule 2
- rule 3
```

### 2. Changes Sync Automatically
Within 3 seconds, your changes appear in all other agents! No manual sync needed.

## Skills Sync

Skills are directory-based: each skill is a folder containing `SKILL.md` and optional assets. Agent Rules Sync syncs **user-level skills** across all frameworks.

### Skills Storage (synced across all)

| Framework | Path |
|-----------|------|
| **Cursor** | `~/.cursor/skills/`, `~/.cursor/skills-cursor/` |
| **Claude Code** | `~/.claude/skills/` |
| **Codex** | `~/.codex/skills/` (or `$CODEX_HOME/skills`) |
| **Gemini Antigravity** | `~/.gemini/antigravity/skills/` |
| **OpenCode** | `~/.config/opencode/skills/` |
| **Shared** | `~/.agents/skills/` (Codex, OpenCode, Claude-compatible) |

### Adding or Editing Skills

1. **Add a skill** in any of the paths above: create a folder with `SKILL.md` inside
2. **Edit** the `SKILL.md` or add scripts/references in the folder
3. Changes sync within 3 seconds to all other frameworks

Example:
```bash
mkdir -p ~/.cursor/skills/my-skill
echo '---
name: my-skill
description: My custom skill
---
# My Skill

Instructions here.
' > ~/.cursor/skills/my-skill/SKILL.md
```

### Skills Backups

Skill directories are backed up to `~/.config/agent-rules-sync/skill_backups/` before any overwrite. See [BACKUPS.md](BACKUPS.md) for details.

**Note:** Plugin-installed skills (e.g. from Cursor/Claude marketplaces) are NOT synced—they are managed by each framework's plugin system.

## How It Works

1. **Daemon monitors** all 9 agent config file locations and all skill directories every 3 seconds
   - Rules: Claude Code, Cursor, Gemini, OpenCode, Config Agents, Codex, Config root, Local Agent (2 variants)
   - Skills: Cursor, Claude, Codex, Gemini, OpenCode, ~/.agents/skills
2. **Detects changes** in any rules file or skill directory
3. **Merges** rules from all sources (shared + agent-specific); unions skills from all locations
4. **Syncs to all agents** automatically
5. **Deduplicates** identical rules; for skills, newest version wins

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

**Windows Task Scheduler Management:**
```powershell
# View running task
schtasks /query /tn "agent-rules-sync"

# Manually delete task (if needed)
schtasks /delete /tn "agent-rules-sync" /f

# Manually create task (if needed)
# See install_daemon.py for task XML details
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

**On macOS or Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/dhruv-anand-aintech/agent-rules-sync/main/uninstall.py | python3
```

**On Windows:**
```powershell
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/dhruv-anand-aintech/agent-rules-sync/main/uninstall.py').read())"
```

**Or manually:**
```bash
python -m pip uninstall -y agent-rules-sync
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

### Shared Rule (syncs everywhere)

**Terminal 1:**
```bash
$ agent-rules-sync watch
🔄 Watching for changes (every 3s)...
```

**Terminal 2:**
```bash
# Add shared rule to Claude
$ cat >> ~/.claude/CLAUDE.md << 'EOF'
# Shared Rules
- use pydantic for validation
EOF

[3 seconds later...]
```

**Result:** Rule appears in all agents:
- ✅ `~/.cursor/rules/global.mdc`
- ✅ `~/.gemini/GEMINI.md`
- ✅ `~/.config/opencode/AGENTS.md`

### Agent-Specific Rule (stays local)

**Terminal 2:**
```bash
# Add Claude-specific rule
$ cat >> ~/.claude/CLAUDE.md << 'EOF'
## Claude Code Specific
- use claude-style syntax highlights
EOF

[3 seconds later...]
```

**Result:** Rule stays in Claude only
- ✅ `~/.claude/CLAUDE.md` has the rule
- ❌ `~/.cursor/rules/global.mdc` does NOT have it
- ❌ Other agents unaffected

✓ Done! Shared rules sync everywhere, agent-specific rules stay local.

## Features

✓ **Shared rules** — sync rules to all agents automatically
✓ **Agent-specific rules** — keep rules local to one agent only
✓ **Skills sync** — sync skill folders across Cursor, Claude, Codex, Gemini, OpenCode
✓ **Rule deletion** — just delete the line, it disappears on next sync
✓ **Bidirectional sync** — rules and skills can be added from any agent
✓ **Auto-deduplication** — same rule doesn't appear twice
✓ **Automatic backups** — timestamped backups before every change (rules + skills)
✓ **Fire and forget** — daemon auto-starts and runs in background
✓ **Zero config** — works out of the box
✓ **Real-time** — syncs within 3 seconds
✓ **Safe recovery** — restore any previous version from backups
✓ **Well-tested** — 28+ integration and unit tests with daemon watch coverage

## Merging Behavior

Rules are **merged**, not replaced. If you have:

**Master:** `- rule A`, `- rule B`
**Claude:** `- rule A`, `- rule B`, `- rule C`

After sync, all agents get: `- rule A`, `- rule B`, `- rule C`

No rules are lost!

## Architecture

```
Shared Rules (in # Shared Rules section)
         ↓
    Daemon detects changes (every 3 seconds)
         ↓
    Extract shared + agent-specific rules
         ↓
    Merge all sources bidirectionally
         ↓
    Rebuild master with all sections
         ↓
    Sync: shared to all, agent-specific to their agent
         ↓
    Done! (rules synced, agent rules stay local)
```

**Master file structure:**
```
~/.config/agent-rules-sync/RULES.md
├─ # Shared Rules (syncs to all agents)
├─ ## Claude Code Specific (Claude only)
├─ ## Cursor Specific (Cursor only)
├─ ## Gemini Specific (Gemini only)
└─ ## OpenCode Specific (OpenCode only)
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

## Supported Agent Locations

Agent Rules Sync monitors and syncs rules across 9+ agent configuration locations:

**Main Editors:**
- Claude Code (`~/.claude/CLAUDE.md`)
- Cursor (`~/.cursor/rules/global.mdc`)
- Gemini Antigravity (`~/.gemini/GEMINI.md`)
- OpenCode (`~/.config/opencode/AGENTS.md`)

**Additional Locations:**
- Config Agents (`~/.config/agents/AGENTS.md`)
- Codex (`~/.codex/AGENTS.md`)
- Config Root (`~/.config/AGENTS.md`)
- Local Agent (`~/.agent/AGENTS.md`)
- Local Agent Alt (`~/.agent/AGENT.md`)

Create any of these files and Agent Rules Sync will automatically sync rules to all other locations!

## Requirements

- Python 3.8+
- At least one agent configuration file location (any of the above)

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
