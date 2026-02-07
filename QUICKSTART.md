# Quick Start Guide

Get started in 1 minute!

## Install

```bash
pip install agent-rules-sync
```

✓ **Done!** The daemon is now running in the background.

## Start Using

1. **Open any agent config file:**
   ```bash
   nano ~/.claude/CLAUDE.md      # or use vim, code, etc.
   ```

2. **Add a rule:**
   ```markdown
   - my new rule here
   ```

3. **Files are automatically synced (within 3 seconds)**

   Your rule now exists in:
   - `~/.cursor/rules/global.mdc`
   - `~/.gemini/GEMINI.md`
   - `~/.config/opencode/AGENTS.md`

4. **Restart your agent for changes to take effect:**

   | Agent | Action |
   |-------|--------|
   | Claude Code | Restart or new session |
   | Cursor | New conversation |
   | Gemini | Run `/memory refresh` or restart |
   | OpenCode | Restart or new session |

## Check Status

```bash
agent-rules-sync status
```

## Stop Daemon

```bash
agent-rules-sync stop
```

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/dhruv-anand-aintech/agent-rules-sync/main/uninstall.sh | bash
```

---

**That's it!** Files sync automatically. Just restart your agent for changes to take effect.

For technical details on how each agent loads configuration, see [AGENT_FILE_RELOAD.md](AGENT_FILE_RELOAD.md)
