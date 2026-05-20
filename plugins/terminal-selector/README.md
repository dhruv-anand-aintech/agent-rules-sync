# Terminal Selector

Portable terminal-native selection tools for coding agents.

This package provides:

- `bin/terminal-selector`: a standalone terminal TUI for single-select, multi-select, and ranked selection.
- `terminal_selector/mcp_server.py`: an MCP server exposing the same selector as tools.
- `skills/terminal-selector/SKILL.md`: agent instructions that work outside Codex plugins.
- `.codex-plugin/plugin.json` and `.mcp.json`: Codex plugin wrapper metadata.

The core implementation is intentionally independent of Codex. Other coding agents can install the skill directory and configure the MCP server directly.

## Standalone CLI

```bash
printf '%s\n' "Codex core" "Plugin hook" "MCP + web UI" "Shell helper" \
  | plugins/terminal-selector/bin/terminal-selector --mode rank --title "Rank options"
```

Input can also be JSON:

```bash
plugins/terminal-selector/bin/terminal-selector --mode multi --input options.json
```

`options.json`:

```json
{
  "title": "Pick options",
  "options": [
    {"id": "core", "label": "Codex core"},
    {"id": "plugin", "label": "Plugin hook"}
  ]
}
```

The command writes JSON to stdout.

Inline options are supported without a temp file:

```bash
plugins/terminal-selector/bin/terminal-selector \
  --mode rank \
  --title "Rank options" \
  --options-json '{"options":[{"id":"core","label":"Codex core"},"MCP direct","Shell helper"]}'
```

For simple labels, repeat `--option`:

```bash
plugins/terminal-selector/bin/terminal-selector \
  --mode multi \
  --title "Pick options" \
  --option "Codex core" \
  --option "MCP direct" \
  --option "Shell helper"
```

## MCP

Run directly:

```bash
python3 plugins/terminal-selector/terminal_selector/mcp_server.py
```

Codex MCP config is included in `.mcp.json`. For other agents, configure the server command to run `python3 <path>/terminal_selector/mcp_server.py`.

Important: MCP normally uses stdio for JSON-RPC. This server opens `/dev/tty` for the TUI so it does not corrupt the MCP protocol. Hosts that launch MCP servers without a controlling terminal will receive a clear error and should call the standalone CLI from an interactive shell instead.
