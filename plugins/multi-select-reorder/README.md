# Multi Select Reorder

Ad hoc browser-based multi-select and reorder tool for coding agents.

This package provides:

- `multi_select_reorder/mcp_server.py`: a stdio MCP server exposing the `multi_select_reorder` tool.
- `skills/multi-select-reorder/SKILL.md`: agent instructions.
- `.codex-plugin/plugin.json` and `.mcp.json`: Codex plugin wrapper metadata.

When the MCP tool is called, it starts a temporary localhost HTTP server, opens a browser page, waits for submit or cancel, returns JSON to the agent, and shuts the temporary server down.

## MCP

Run directly:

```bash
python3 plugins/multi-select-reorder/multi_select_reorder/mcp_server.py
```

Codex MCP config is included in `.mcp.json`. For other agents, configure the server command to run `python3 <path>/multi_select_reorder/mcp_server.py`.

The tool returns:

```json
{
  "mode": "multi_select_reorder",
  "selected": ["id-a", "id-b"],
  "ordered": ["id-b", "id-a"],
  "descriptions": {"id-a": "Edited description"},
  "cancelled": false
}
```

Options are selected by default. To override the initial state, pass option
objects with `selected: false`, or pass `initial_selected` as a list of option
ids:

```json
{
  "title": "Pick work",
  "options": [
    {"id": "a", "label": "Alpha"},
    {"id": "b", "label": "Beta", "selected": false}
  ],
  "initial_selected": ["a"]
}
```

For compact calls, options can be tuple-style JSON arrays:

```json
{
  "title": "Pick work",
  "options": [
    ["a", "Alpha"],
    ["b", "Beta", "Optional detail", false]
  ]
}
```

Tuple positions are `[id, label, description, selected]`; omitted values use
the same defaults as object options.

To edit descriptions in the same browser window, pass `edit_descriptions: true`.
The returned `descriptions` object contains the final description text keyed by
option id.

## Legacy CLI

`bin/multi-select-reorder` still provides the older terminal selector CLI for direct shell usage. The MCP tool uses the browser workflow by default.
