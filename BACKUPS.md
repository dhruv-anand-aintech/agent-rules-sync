# Backup System

Agent Rules Sync automatically creates timestamped backups every time it modifies agent configuration files. This ensures you can always recover previous versions if needed.

## How Backups Work

### When Backups are Created

- **Every time the daemon syncs** files to any agent
- **Before any file is modified** (protection against accidental changes)
- **Timestamped** with the exact moment of change
- **One backup per modification** - all versions are preserved

### Backup Location

```
~/.config/agent-rules-sync/backups/
├── claude_20260125_014532.md       # Claude Code backup
├── cursor_20260125_014532.mdc      # Cursor backup
├── gemini_20260125_014532.md       # Gemini backup
├── opencode_20260125_014532.md     # OpenCode backup
└── master_20260125_014532.md       # Master rules backup
```

### Naming Convention

Backups follow this pattern:
```
{agent-name}_{YYYYMMDD}_{HHMMSS}.{extension}
                ↑                    ↑
                Date                Time (24-hour format)
```

**Examples:**
- `claude_20260125_023045.md` - January 25, 2026 at 2:30:45 AM
- `cursor_20260125_143000.mdc` - January 25, 2026 at 2:30:00 PM

## Viewing Backups

### List all backups

```bash
ls -lah ~/.config/agent-rules-sync/backups/
```

Output:
```
-rw-r--r--  1 user  staff  1.2K Jan 25 01:45 claude_20260125_014532.md
-rw-r--r--  1 user  staff  1.2K Jan 25 01:45 cursor_20260125_014532.mdc
-rw-r--r--  1 user  staff  1.2K Jan 25 01:45 gemini_20260125_014532.md
-rw-r--r--  1 user  staff  1.2K Jan 25 01:45 master_20260125_014532.md
```

### View a specific backup

```bash
cat ~/.config/agent-rules-sync/backups/claude_20260125_014532.md
```

### View latest backups

```bash
# Latest 5 backups (most recent first)
ls -lt ~/.config/agent-rules-sync/backups/ | head -5
```

### View backups from a specific time

```bash
# All backups from January 25
ls ~/.config/agent-rules-sync/backups/ | grep 20260125
```

## Backup Activity Logging

Each backup operation is logged to the daemon log with:
- **Timestamp** - when the backup was created
- **File name** - which agent was backed up
- **Backup location** - full path to the backup

### View backup logs

```bash
# All backup activities
grep "Backed up" ~/.config/agent-rules-sync/daemon.log

# Follow live backup logs
tail -f ~/.config/agent-rules-sync/daemon.log | grep "Backed up"
```

Example log entries:
```
[2026-01-25 01:45:32] Backed up master: master_20260125_014532.md
[2026-01-25 01:45:32] Backed up claude: claude_20260125_014532.md
[2026-01-25 01:45:32] Backed up cursor: cursor_20260125_014532.mdc
[2026-01-25 01:45:32] Backed up gemini: gemini_20260125_014532.md
[2026-01-25 01:45:32] Backed up opencode: opencode_20260125_014532.md
```

## Recovering from Backups

### If you accidentally deleted a rule

1. **Find the backup** with the rule you want
   ```bash
   grep -l "your-rule-text" ~/.config/agent-rules-sync/backups/*.md
   ```

2. **Restore the backup**
   ```bash
   # Restore to Claude Code
   cp ~/.config/agent-rules-sync/backups/claude_20260125_014532.md ~/.claude/CLAUDE.md
   ```

3. **Daemon will automatically** sync the restored version to other agents

### If you want to revert to a previous state

1. **List backups** to find the one you want
   ```bash
   ls -lt ~/.config/agent-rules-sync/backups/
   ```

2. **Restore all agents** from a specific timestamp
   ```bash
   # Get the timestamp (e.g., 20260125_010000)
   TIMESTAMP="20260125_010000"

   # Restore Claude
   cp ~/.config/agent-rules-sync/backups/claude_${TIMESTAMP}.md ~/.claude/CLAUDE.md

   # Restore Cursor
   cp ~/.config/agent-rules-sync/backups/cursor_${TIMESTAMP}.mdc ~/.cursor/rules/global.mdc

   # Restore Gemini
   cp ~/.config/agent-rules-sync/backups/gemini_${TIMESTAMP}.md ~/.gemini/GEMINI.md

   # Restore OpenCode
   cp ~/.config/agent-rules-sync/backups/opencode_${TIMESTAMP}.md ~/.config/opencode/AGENTS.md
   ```

3. **Restart your agents** for changes to take effect

### Restore from command line

**Show difference between current and backup:**
```bash
diff ~/.claude/CLAUDE.md ~/.config/agent-rules-sync/backups/claude_20260125_014532.md
```

**View exact changes:**
```bash
# See what was added/removed in the backup
cat ~/.config/agent-rules-sync/backups/claude_20260125_014532.md
```

## Backup Cleanup

### Space Usage

Check how much space backups are using:
```bash
du -sh ~/.config/agent-rules-sync/backups/
```

### Manual Cleanup

**Delete old backups (keep only last 30 days):**
```bash
# Find and delete backups older than 30 days
find ~/.config/agent-rules-sync/backups/ -name "*.md" -mtime +30 -delete
find ~/.config/agent-rules-sync/backups/ -name "*.mdc" -mtime +30 -delete
```

**Delete all backups (careful!):**
```bash
rm -rf ~/.config/agent-rules-sync/backups/*
```

**Delete backups from a specific date:**
```bash
# Delete all Jan 24 backups
rm ~/.config/agent-rules-sync/backups/*20260124*
```

## Backup Safety

### What's Protected

✓ All agent configuration files (`CLAUDE.md`, `global.mdc`, `GEMINI.md`, `AGENTS.md`)
✓ Master rules file
✓ All historical versions with timestamps

### What's Not Protected

- Backups are stored locally (not synced remotely)
- Deleted backups cannot be recovered (use your system's trash/recycle bin for recovery)
- Very old backups will need manual cleanup

### Best Practices

1. **Regular backups to cloud** (manual step)
   ```bash
   # Example: backup to ~/Dropbox/
   cp -r ~/.config/agent-rules-sync/backups/ ~/Dropbox/agent-rules-sync-backups-$(date +%Y%m%d)/
   ```

2. **Archive old backups** before cleanup
   ```bash
   # Tar and compress old backups
   tar -czf ~/agent-rules-backups-20260125.tar.gz ~/.config/agent-rules-sync/backups/
   rm -rf ~/.config/agent-rules-sync/backups/*
   ```

3. **Monitor backup disk usage** regularly
   ```bash
   du -sh ~/.config/agent-rules-sync/
   ```

## Automatic Cleanup (Future Feature)

In future versions, automatic backup cleanup may be added:
- Keep only last N backups per agent
- Delete backups older than X days
- Archive to compressed format

---

**Summary:** Your rules are safe! Every change is backed up with a timestamp. You can always recover previous versions.
