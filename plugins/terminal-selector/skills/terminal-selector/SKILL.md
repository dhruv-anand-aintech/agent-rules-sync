---
name: terminal-selector
description: Use when the user wants an interactive terminal-native choice, multi-select, or ranked ordering flow instead of a web UI or chat-only prompt.
---

# Terminal Selector

Use this skill when a coding agent should present choices through a native terminal TUI.

Prefer the MCP tools when available:

- `terminal_select`: single-choice selection.
- `terminal_multi_select`: multi-choice selection.
- `terminal_rank`: ordered ranking.

If MCP is unavailable or the MCP host has no controlling terminal, run the portable CLI directly:

```bash
plugins/terminal-selector/bin/terminal-selector --mode rank --input options.json
```

The selector writes JSON to stdout with:

- `mode`: `single`, `multi`, or `rank`.
- `selected`: selected option ids.
- `ordered`: ranked option ids, only for rank mode.
- `cancelled`: whether the user cancelled.

Do not use this skill for web UI selection. It is specifically for terminal-native interaction.
