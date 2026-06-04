# agent-sync

**Synchronize rules, skills, settings, and MCP servers across Claude Code, Cursor, Gemini, OpenCode, and Codex — in real-time.**

Edit rules, skills, or MCP servers in any AI agent → they automatically sync to all others. Global Claude settings propagate to configured repos for Claude Code web access.

## Installation

Works on **macOS**, **Linux**, and **Windows** (native + WSL).

```bash
pip install agent-rules-sync
```

```bash
uv pip install agent-rules-sync   # faster
```

The daemon installs and starts automatically as a system service.

## CLI

```bash
agent-sync                         # start/ensure daemon is running
agent-sync sync                    # one-shot sync: rules + skills + settings + mcp
agent-sync sync rules              # sync only CLAUDE.md / rules files
agent-sync sync skills             # sync only skills directories
agent-sync sync settings           # sync only .claude/settings.json + hooks
agent-sync sync mcp                # sync only mcp.json / MCP server configs
agent-sync sync history            # import agent-run shell commands into Atuin
agent-sync sync rules skills       # multiple scopes
agent-sync setup                   # TUI wizard to configure sync directions
agent-sync status                  # daemon and sync status
agent-sync stop                    # stop daemon
agent-sync watch                   # watch in foreground (debugging)
```

`agent-rules-sync` also works as an alias for backwards compatibility.

## What Gets Synced

### 1. Rules (`CLAUDE.md`, `GEMINI.md`, etc.)

Rules sync **bidirectionally** across all agent config files. Changes from any agent propagate to all others within 3 seconds.

```markdown
# Shared Rules
- use pydantic for validation      ← syncs to all agents

## Claude Code Specific
- claude-specific rule             ← stays in Claude only
```

Monitored locations:
| Agent | Path |
|-------|------|
| Claude Code | `~/.claude/CLAUDE.md` |
| Cursor | `~/.cursor/rules/global.mdc` (merged **output**); also reads every `*.md` / `*.mdc` in the **same** `~/.cursor/rules/` dir (subfolders except `imported/`). Strip YAML frontmatter before parsing. |
| Cursor (legacy) | `~/.cursorrules` plus `<repo>/.cursorrules` for each path in `repo_paths.json` — same body as `global.mdc`; Cursor still loads these ([docs](https://cursor.com/docs/rules)) |
| Gemini CLI | `~/.gemini/GEMINI.md` |
| Antigravity CLI | `~/.gemini/antigravity-cli/plugins/agent-rules-sync/rules/AGENTS.md` |
| OpenCode | `~/.config/opencode/AGENTS.md` |
| Codex | `~/.codex/AGENTS.md` |
| + 4 more | `~/.config/agents/AGENTS.md`, `~/.config/AGENTS.md`, `~/.agent/AGENTS.md`, `~/.agent/AGENT.md` |

Repo-specific `CLAUDE.md` files can be added via `repo_paths.json` (see [Configuration](#configuration)).

### 2. Skills

Skills are directories containing a `SKILL.md` file. Synced across all frameworks:

| Framework | Path |
|-----------|------|
| Claude Code | `~/.claude/skills/` |
| Cursor | `~/.cursor/skills/`, `~/.cursor/skills-cursor/` |
| Codex | `~/.codex/skills/` |
| Antigravity CLI | `~/.gemini/antigravity-cli/plugins/agent-rules-sync/skills/` |
| Gemini Antigravity | `~/.gemini/antigravity/skills/` |
| OpenCode | `~/.config/opencode/skills/` |
| Shared | `~/.agents/skills/` |

Newest version wins. Add a skill anywhere and the daemon syncs it to the other locations automatically.

### 3. Settings & Hooks (Claude Code + Roadmap)

#### Current: Portable Settings

Syncs a **portable version** of `~/.claude/settings.json` to configured repos' `.claude/settings.json`:

- Strips machine-specific keys (`statusLine`, `spinnerVerbs`, `remote`, etc.)
- Strips permission rules with absolute paths
- **Rewrites hook commands** from `~/.claude/hooks/foo.sh` → `.claude/hooks/foo.sh`
- **Copies hook scripts** into the repo's `.claude/hooks/`

This enables full tool permissions and hooks when using **Claude Code web** on those repos.

#### Roadmap: Cross-Agent Settings Sync

Coming soon: Synchronize keyboard shortcuts, themes, auto-save, debugging, and other agent-specific settings across Claude Code, Cursor, Cline, Aider, and more.

**Discovery phase complete.** See:
- `SETTINGS_SYNC_TODO.md` — Implementation roadmap for 9 new settings categories
- `SETTINGS_REFERENCE.md` — Platform-specific settings mappings and sync strategies

**Priority settings for sync:**
1. Keyboard shortcuts (Cursor, Claude Code, VS Code extensions)
2. Theme customization (Dark/light mode across IDEs)
3. Auto-save behavior (CLI and IDE agents)

See `SETTINGS_SYNC_TODO.md` for full implementation plan and effort estimates.

### 4. MCP Servers (`mcp.json`)

Synchronizes your **MCP server list** (under the `mcpServers` key) across all agents and the Claude Desktop. Any server added in Cursor or via `claude mcp add` becomes available everywhere.

| Agent | Configuration Path |
|-------|-------------------|
| Claude Code | `~/.claude.json` |
| Cursor | `~/.cursor/mcp.json` |
| Gemini CLI | `~/.gemini/mcp.json` |
| Antigravity CLI | `~/.gemini/antigravity-cli/plugins/agent-rules-sync/mcp_config.json` |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) |

Project-specific MCP servers in `.mcp.json`, `.cursor/mcp.json`, or `.gemini/mcp.json` are also merged into the global master list and synced across agents.

### 5. Agent Command History (Atuin)

Imports shell commands run by coding agents into Atuin so they show up in zsh reverse search alongside normal terminal history. The importer reads local transcript stores, writes a normalized append-only log at `~/.config/agent-rules-sync/agent-command-history.jsonl`, and inserts new commands into `~/.local/share/atuin/history.db`.

Supported transcript sources:
| Agent | Source |
|-------|--------|
| Codex | `~/.codex/sessions/**/*.jsonl` |
| Claude Code | `~/.claude/projects/**/*.jsonl` |
| Cursor CLI | `~/.cursor/projects/**/agent-transcripts/**/*.jsonl` |

Current stable Atuin releases do not yet expose first-class agent metadata in search, so imported commands include a harmless trailing tag like `# agent:codex`. Newer Atuin builds with `author` / `intent` columns receive those fields directly.

The daemon watches these transcript roots too. When a transcript changes it imports only the changed transcript into the JSONL log and Atuin, without running a rules/skills/settings sync.

## Configuration

### Repo Paths

Add repos to sync rules, skills, and settings into:

```bash
~/.config/agent-rules-sync/repo_paths.json
```

```json
["~/Code/my-project", "~/Code/another-repo"]
```

Each repo gets:
- `<repo>/CLAUDE.md` — synced from global rules
- `<repo>/.cursorrules` — legacy Cursor rules file; mirrored from the same content as `global.mdc` (optional; Cursor prefers `.cursor/rules/`)
- `<repo>/.claude/skills/` — synced from master skills
- `<repo>/.claude/settings.json` — portable settings (auto-generated)
- `<repo>/.claude/hooks/` — hook scripts (copied from `~/.claude/hooks/`)

### Sync Directions

Configure per-component direction via `agent-sync setup` (TUI wizard) or edit directly:

```bash
~/.config/agent-rules-sync/sync_config.json
```

```json
{
  "mode": "default",
  "components": {
    "rules":    { "direction": "bidirectional", "enabled": true },
    "skills":   { "direction": "bidirectional", "enabled": true },
    "settings": { "direction": "push",          "enabled": true },
    "hooks":    { "direction": "push",           "enabled": true },
    "mcp":      { "direction": "bidirectional", "enabled": true }
  }
}
```

**Directions:**

| Direction | Behavior |
|-----------|----------|
| `bidirectional` | Newest version wins, syncs everywhere (default for rules/skills) |
| `push` | Master → agents only (master is source of truth) |
| `pull` | Agents → master only (aggregate, don't push back) |

Settings and hooks only support `push` (they are generated from global config).

### Settings Strip Rules

Customize which keys/paths are stripped when generating portable settings:

```bash
~/.config/agent-rules-sync/settings_sync.json
```

```json
{
  "strip_keys": ["statusLine", "spinnerVerbs", "remote"],
  "strip_path_prefixes": ["/Users/", "/home/", "/opt/homebrew/"],
  "sync_hooks": true,
  "hook_script_dir": ".claude/hooks"
}
```

## Setup Wizard

Run `agent-sync setup` for a guided TUI to configure sync directions:

```
┌──────────────────────────────────────────────────────────┐
│ agent-sync  ·  Setup Wizard                              │
└──────────────────────────────────────────────────────────┘

  ── Sync Mode ───────────────────────────────────────────

  default       Rules/skills are bidirectional (newest wins).
                Settings/hooks push from global → repos.

  per_component Configure each component independently.

  Choice [1-2] (Enter = default):
```

## Commands Reference

```bash
agent-sync sync [rules] [skills] [settings] [mcp] [all]
```

| Scope | What it syncs |
|-------|--------------|
| `rules` | Rules files (`CLAUDE.md`, `GEMINI.md`, etc.) across all agents |
| `skills` | Skill directories across all frameworks + configured repos |
| `settings` | `~/.claude/settings.json` → repo `.claude/settings.json` + hooks |
| `mcp` | MCP server configurations (`mcp.json`, `~/.claude.json`) |
| `history` | Agent-run shell commands → Atuin history/backsearch |
| `all` | All of the above (default when no scope given) |

## How It Works

```
~/.claude/settings.json         ~/.claude/CLAUDE.md        ~/.claude/skills/
        │                               │                         │
        │  strip machine-specific       │  merge shared +         │  newest
        │  rewrite hook paths           │  agent-specific         │  version
        ▼                               ▼                         ▼
  repo/.claude/             all agent CLAUDE.md          all framework
  settings.json             GEMINI.md AGENTS.md          skills/ dirs
  hooks/                    (9+ locations)               (6+ locations)
```

Daemon watches all locations with filesystem events. A slow periodic rescan is
kept as a fallback for missed events or platforms without an event backend.

## Backups

Every file change is backed up with a timestamp:
```
~/.config/agent-rules-sync/backups/     ← rules backups
~/.config/agent-rules-sync/skill_backups/  ← skills backups
```

Restore any version:
```bash
cp ~/.config/agent-rules-sync/backups/claude_20260125_014532.md ~/.claude/CLAUDE.md
```

## Troubleshooting

```bash
agent-sync status              # check daemon + sync status
tail -f ~/.config/agent-rules-sync/daemon.log   # live logs
agent-sync stop && agent-sync  # restart daemon
agent-sync watch               # run in foreground for debugging
```

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/dhruv-anand-aintech/agent-rules-sync/main/uninstall.sh | bash
```

Or manually:
```bash
agent-sync stop
pip uninstall -y agent-rules-sync
rm -rf ~/.config/agent-rules-sync
```

Agent rule files and repos are not touched.

## Requirements

- Python 3.8+
- macOS, Linux, or Windows

## License

MIT — see [LICENSE](LICENSE)

---

**Edit anywhere. Sync everywhere.**
