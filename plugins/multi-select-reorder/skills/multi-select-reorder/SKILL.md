---
name: multi-select-reorder
description: Use when the user wants an interactive ad hoc web page for choosing multiple options and reordering them before submitting.
---

# Multi Select Reorder

Use this skill when a coding agent should present choices in a temporary local web UI, let the user select multiple items, reorder them with drag-and-drop, and return the submitted result.

Prefer the MCP tool when available:

- `multi_select_reorder`: checkbox multi-select plus drag-and-drop ordering.

Options are initially selected by default. To set initial state manually, pass
option objects with `selected: false`, or pass `initial_selected` as a list of
option ids. For compact calls, options can be tuple-style JSON arrays in the
form `[id, label, description, selected]`, with omitted trailing values using
the normal defaults.

Pass `edit_descriptions: true` when the user should be able to edit option
descriptions in the same browser window.

The selector writes JSON with:

- `mode`: `multi_select_reorder`.
- `selected`: selected option ids.
- `ordered`: selected option ids in the submitted order.
- `descriptions`: final descriptions keyed by option id.
- `cancelled`: whether the user cancelled.

Do not use this skill for terminal-native TUI selection. It is specifically for browser-based multi-select reorder flows.
