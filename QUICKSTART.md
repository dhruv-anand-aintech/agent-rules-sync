# Quick Start Guide

Get started in 2 minutes!

## Install

```bash
pip install git+https://github.com/yourusername/agent-rules-sync.git && agent-rules-sync
```

## Start Using

1. **Open any agent config file:**
   ```bash
   nano ~/.claude/CLAUDE.md      # or use vim, code, etc.
   ```

2. **Add a rule:**
   ```markdown
   - my new rule here
   ```

3. **Save and wait 3 seconds**

   That's it! The rule appears in:
   - `~/.cursor/rules/global.mdc`
   - `~/.gemini/GEMINI.md`
   - `~/.config/opencode/AGENTS.md`

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
curl -fsSL https://raw.githubusercontent.com/yourusername/agent-rules-sync/main/uninstall.sh | bash
```

---

That's all you need to know! The daemon handles the rest automatically.
