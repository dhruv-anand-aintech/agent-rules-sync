# Agent Settings Sync Reference

Quick reference for settings discovered across 24 coding agents.

---

## Settings Sync Candidates

### 🔴 High Priority (User Demand + Broad Support)

#### 1. Keyboard Shortcuts / Keybindings
**Supported by:** Claude Code, Cursor, Cline, Roo Code, VS Code, JetBrains IDEs

**Config locations:**
- Claude Code: `~/.claude/keybindings.json`
- Cursor: `~/.cursor/keybindings.json` (VS Code format)
- VS Code: `~/.config/Code/User/keybindings.json`
- JetBrains: IDE-specific keymaps

**Format:**
```json
[
  { "key": "cmd+k cmd+c", "command": "editor.action.commentLine" },
  { "key": "ctrl+shift+k", "command": "editor.action.deleteLine" }
]
```

**Sync strategy:** Bidirectional (VS Code format as canonical)

#### 2. Theme / Appearance Customization
**Supported by:** Claude Code, Cursor, VS Code extensions, Desktop agents

**Config locations:**
- Claude Code: Settings UI + theme JSON
- Cursor: `~/.cursor/settings.json` (workbench.colorTheme)
- VS Code: `~/.config/Code/User/settings.json`

**Sync strategy:** Bidirectional (theme name + color overrides)

#### 3. Auto-Save Configuration
**Supported by:** Claude Code, Cursor, VS Code, Cline, Roo Code, Aider

**Options:**
- Auto-save on blur
- Auto-save after delay (e.g., 1s, 5s)
- Auto-save on focus loss
- Manual save only

**Sync strategy:** Push from master config

---

### 🟡 Medium Priority (Optimization + Common)

#### 4. Context Window / Token Limits
**Supported by:** Claude Code, Cursor, Cline, Roo Code, Aider, Codex

**Settings:**
```json
{
  "max_context_tokens": 200000,
  "max_output_tokens": 4096,
  "preferred_budget": 100000
}
```

**Sync strategy:** Push with per-model overrides

#### 5. Debugging Output / Verbose Logging
**Supported by:** Claude Code, Cursor, Aider, Cline, CLI agents

**Levels:**
- off
- info
- debug
- trace
- verbose

**Output location:** `~/.config/agent-rules-sync/agent_debug.log`

**Sync strategy:** Push from master

#### 6. Git Integration Settings
**Supported by:** All agents (18+)

**Settings:**
```json
{
  "auto_commit_enabled": true,
  "auto_commit_message_template": "[agent] {action}",
  "create_feature_branches": true,
  "git_diff_verbosity": "full",
  "show_ignored_files": false
}
```

**Sync strategy:** Bidirectional (newest wins)

#### 7. Code Formatting
**Supported by:** Claude Code, Cursor, Cline, Roo Code, Aider

**Settings:**
```json
{
  "formatter": "prettier",
  "auto_format_on_save": true,
  "formatOnPaste": true,
  "line_length": 100,
  "indent_size": 2,
  "indent_style": "space"
}
```

**Sync strategy:** Bidirectional

---

### 🟢 Lower Priority (UI/UX)

#### 8. UI Customization
**Supported by:** Claude Code, Cursor, VS Code extensions, GUI agents

**Settings:**
- Sidebar width/collapsed
- Panel layout (vertical/horizontal)
- Minimap visibility
- Breadcrumb visibility

#### 9. Performance Mode / Caching
**Supported by:** Claude Code, Cursor, Cline

**Settings:**
- Cache enabled/disabled
- Cache TTL
- Memory limits
- Optimization level

---

## Platform Settings Mappings

### Claude Code
**Settings file:** `~/.claude/settings.json`
```json
{
  "model": "claude-opus-4.8",
  "maxTokens": 200000,
  "autoSave": true,
  "telemetry": false,
  "theme": "auto",
  "keybindings": "...keybindings.json"
}
```

### Cursor
**Settings file:** `~/.cursor/settings.json` (VS Code compatible)
```json
{
  "workbench.colorTheme": "Cursor Dark",
  "[python]": { "editor.defaultFormatter": "ms-python.python" },
  "editor.formatOnSave": true,
  "files.autoSave": "afterDelay"
}
```

### Aider (CLI)
**Settings file:** `~/.aider.conf.json` or via CLI args
```json
{
  "model": "claude-opus-4.8",
  "max-input-tokens": 200000,
  "auto-commit": true,
  "verbose": false
}
```

### VS Code Extensions (Cline, Roo Code)
**Settings location:** VS Code settings + `.cline.json` / `.roo.json`
- Inherit VS Code keybindings, theme, formatting
- Extension-specific: `~/.vscode/extensions/<ext>/<config>.json`

---

## Sync Data Structures

### Master Config File
Location: `~/.config/agent-rules-sync/agent_settings.json`

```json
{
  "version": 1,
  "last_updated": "2026-06-04T10:30:00Z",
  "keybindings": {
    "enabled": true,
    "canonical_format": "vscode",
    "mappings": {
      "vscode": "~/.config/Code/User/keybindings.json",
      "claude_code": "~/.claude/keybindings.json",
      "cursor": "~/.cursor/keybindings.json"
    }
  },
  "theme": {
    "enabled": true,
    "dark_mode": "auto",
    "theme_name": "Material One Dark"
  },
  "auto_save": {
    "enabled": true,
    "strategy": "afterDelay",
    "delay_ms": 1000
  },
  ...
}
```

### Per-Agent Overrides
Location: `~/.config/agent-rules-sync/agent_settings.per_agent.json`

```json
{
  "claude-code": {
    "model": "claude-opus-4.8",
    "maxTokens": 150000
  },
  "cursor": {
    "model": "gpt-4-turbo",
    "contextWindow": 128000
  },
  "aider": {
    "model": "claude-opus-4.8",
    "autoCommit": true
  }
}
```

---

## Implementation Checklist

- [ ] Design unified settings schema (canonicalize formats)
- [ ] Create agent-to-canonical transformers (9 agents)
- [ ] Create canonical-to-agent converters (9 agents)
- [ ] Implement file watcher for settings changes
- [ ] Add backup mechanism (`.backups/settings_*.json`)
- [ ] Implement bidirectional sync (keyboard, git, formatting)
- [ ] Implement push-only sync (auto-save, debugging, context)
- [ ] Add conflict resolution logic
- [ ] Create CLI commands (`agent-sync sync settings`)
- [ ] Write tests for each agent
- [ ] Document limitations per agent
- [ ] Create user docs and troubleshooting guide

---

## Known Limitations

### By Agent

**Claude Code:**
- No external provider support (only Claude models)
- Keybindings format is proprietary

**Cursor:**
- Some settings are VS Code-specific; mapping needed
- Theme names may differ from VS Code

**Cline / Roo Code:**
- Inherit VS Code settings; extension settings limited
- Token budget per extension config (not centralized)

**Aider:**
- CLI-based; no GUI settings
- Config via file or command-line args

**Other agents:**
- Many settings unknown (research needed)
- Some proprietary agents may not support external sync

---

## Research Status

✅ **Complete research:**
- Claude Code
- Cursor
- Aider
- Cline
- Roo Code

🔲 **Need research:**
- Amp, Antigravity, Codex, Cohere North, Devin
- Factory Droid, Gemini CLI, GitHub Copilot, Grok Build
- Jules, Junie, Kilo Code, Kimi CLI, Kiro
- OpenCode, Pi, Qwen Code, Replit Agent, Windsurf

---

## Related Documentation

- **Matrix:** `/docs/tools/agent_matrix/` — Feature matrix for all agents
- **TODO:** `/SETTINGS_SYNC_TODO.md` — Implementation roadmap
- **Schema:** `/docs/tools/agent_matrix/schema.json` — Agent matrix schema

