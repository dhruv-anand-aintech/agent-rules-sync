# Settings Sync Implementation TODO

**Goal:** Implement synchronization of agent settings across Claude Code, Cursor, Gemini, OpenCode, Codex, and other coding agents.

**Status:** 📋 Discovered common settings across 24 agents. Ready for implementation.

---

## 🎯 Priority Settings to Implement

### High Priority (Core Settings)

These are the most commonly requested and widely supported across agents.

- [ ] **1. Keyboard Shortcuts / Keybindings**
  - **Supported by:** Claude Code, Cursor, Cline, Roo Code, VS Code extensions
  - **Formats:** 
    - Claude Code: `.claude/keybindings.json`
    - Cursor: `~/.cursor/keybindings.json` (VS Code format)
    - VS Code: `~/.config/Code/User/keybindings.json`
  - **Task:** Create mapping layer to normalize keybindings across formats
  - **Estimated effort:** Medium

- [ ] **2. Theme / Appearance Customization**
  - **Supported by:** Claude Code, Cursor, VS Code extensions, IDE agents
  - **Formats:**
    - Claude Code: Settings UI + theme config
    - Cursor: Theme selection + color customization
    - VS Code: `~/.config/Code/User/settings.json` (`workbench.colorTheme`)
  - **Task:** Sync theme preferences across IDE boundaries
  - **Estimated effort:** Medium

- [ ] **3. Auto-Save Configuration**
  - **Supported by:** Claude Code, Cursor, VS Code, Cline, Roo Code, Aider
  - **Settings:**
    - Auto-save on blur / interval / focus loss
    - Auto-commit after agent sessions
  - **Task:** Standardize auto-save behavior across platforms
  - **Estimated effort:** Low-Medium

### Medium Priority (Optimization Settings)

- [ ] **4. Context Window / Token Limits**
  - **Supported by:** Claude Code, Cursor, Cline, Aider, Roo Code
  - **Task:** Sync preferred token budget and context length
  - **Estimated effort:** Medium
  - **Note:** Model-dependent; may need per-model configuration

- [ ] **5. Debugging Output / Verbose Logging**
  - **Supported by:** Claude Code, Cursor, Aider, Cline, Roo Code
  - **Settings:**
    - Debug mode on/off
    - Log level (info, debug, trace, verbose)
    - Log output location
  - **Task:** Standardize debug level across agents
  - **Estimated effort:** Low-Medium

- [ ] **6. Git Integration Settings**
  - **Supported by:** All agents (Claude Code, Cursor, Cline, Aider, etc.)
  - **Settings:**
    - Auto-commit on changes
    - Commit message template
    - Diff verbosity
    - Branch auto-create
  - **Task:** Sync git workflow preferences
  - **Estimated effort:** Medium

- [ ] **7. Code Formatting Configuration**
  - **Supported by:** Claude Code, Cursor, Cline, Aider, Roo Code
  - **Settings:**
    - Formatter choice (prettier, black, rustfmt, etc.)
    - Auto-format on save
    - Line length, indentation
  - **Task:** Sync formatter preferences
  - **Estimated effort:** Medium

### Lower Priority (Nice-to-Have)

- [ ] **8. UI Customization**
  - **Supported by:** Claude Code, Cursor, VS Code extensions
  - **Settings:** Sidebar width, panel layout, collapsible sections
  - **Estimated effort:** Medium-High

- [ ] **9. Performance Mode / Caching**
  - **Supported by:** Claude Code, Cursor, Cline
  - **Settings:** Cache management, optimization level
  - **Estimated effort:** Medium

---

## 🔧 Implementation Steps

### Phase 1: Infrastructure (Week 1-2)

- [ ] **1.1** Design unified settings schema for cross-agent compatibility
  - Map Claude Code → Cursor → VS Code → Gemini settings
  - Handle format differences (JSON, YAML, config files)
  - Create mapping file: `settings_mappings.json`

- [ ] **1.2** Create settings normalization layer
  - Abstract away agent-specific config formats
  - Build transformation functions for each agent
  - Handle type conversions (bool, string, number, enum)

- [ ] **1.3** Extend existing sync framework
  - Add to `agent_rules_sync.py` or new `agent_settings_sync.py` module
  - Hook into existing file watcher
  - Use same backup/restore pattern as rules/skills

### Phase 2: Core Settings (Week 2-3)

- [ ] **2.1** Implement keyboard shortcuts sync (High Priority)
  - VS Code format as canonical
  - Transform to Claude Code `.claude/keybindings.json`
  - Test keybinding parsing and merging

- [ ] **2.2** Implement theme customization sync (High Priority)
  - Map theme names across VS Code → Claude Code → Cursor
  - Sync dark/light mode preferences
  - Handle custom color schemes

- [ ] **2.3** Implement auto-save sync (High Priority)
  - Unified auto-save configuration
  - Per-agent override logic
  - Test across Claude Code, Cursor, VS Code

### Phase 3: Optimization Settings (Week 3-4)

- [ ] **3.1** Implement context window sync (Medium Priority)
  - Store preferred token budgets per model
  - Config schema: `{ "model": "claude-opus-4.8", "max_tokens": 200000, "preferred_context": 100000 }`

- [ ] **3.2** Implement debug logging sync (Medium Priority)
  - Centralized log level configuration
  - Route debug output to `~/.config/agent-rules-sync/agent_debug.log`

- [ ] **3.3** Implement git integration sync (Medium Priority)
  - Auto-commit configuration
  - Commit template sharing
  - Diff verbosity preferences

### Phase 4: Testing & Polish (Week 4+)

- [ ] **4.1** Unit tests for each settings type
  - Test format conversion for each agent
  - Test round-trip consistency (A → B → A)
  - Parameterized tests across all agents

- [ ] **4.2** Integration tests
  - Modify setting in Claude Code, verify sync to Cursor
  - Verify sync doesn't break existing rules/skills/MCP sync
  - Test conflict resolution

- [ ] **4.3** Documentation
  - User guide for settings sync configuration
  - Troubleshooting guide for unsupported settings
  - FAQ for agent-specific limitations

---

## 📋 Agent-Specific Implementation Notes

### Claude Code
**Settings location:** `~/.claude/settings.json` + `.claude/keybindings.json`
- ✅ Already has settings UI
- ✅ Supports hooks for settings changes
- 🔲 Need to map keyboard shortcut format
- 🔲 Need auto-sync mechanism for settings changes

### Cursor
**Settings location:** `~/.cursor/settings.json` (similar to VS Code)
- ✅ Uses VS Code-compatible format for most settings
- ✅ VS Code keybindings compatible
- 🔲 Need to research Cursor-specific settings
- 🔲 Need separate handling for `mcp.json`

### Cline (VS Code Extension)
**Settings location:** Inherited from VS Code + `.cline.json`
- ✅ Uses VS Code settings as base
- 🔲 Need to extract Cline-specific settings
- 🔲 Token budget config location?

### Roo Code (VS Code Extension)
**Settings location:** VS Code settings + extension-specific config
- 🔲 Research extension settings structure

### Aider (CLI)
**Settings location:** `~/.aider.conf.json` or `aider.conf`
- ✅ CLI config file available
- ✅ Can read/write config via Python
- 🔲 Map CLI args to settings format

### Gemini CLI
**Settings location:** Research needed
- 🔲 Check for settings file location
- 🔲 Check for environment variable configs

### Codex
**Settings location:** Research needed
- 🔲 Check settings persistence mechanism

### Others (OpenCode, Antigravity, etc.)
- 🔲 Research each platform's settings mechanism

---

## 🔄 Sync Strategy

### Bidirectional vs Unidirectional

**Proposed approach:**
- **Keyboard shortcuts, Theme, Auto-save:** Bidirectional (newest wins)
- **Debug logging, Context window, Git settings:** Push from `~/.config/agent-rules-sync/settings.json` (master)
- **Per-agent overrides:** Local agent settings can override master for non-critical settings

### Conflict Resolution

When different agents have conflicting settings:
1. Timestamp-based: Newest setting wins (bidirectional mode)
2. Master-based: Config master wins (push mode)
3. User prompt: Ask user which setting to keep (for critical settings)

### Backup & Restore

- Create timestamped backups: `~/.config/agent-rules-sync/settings_backups/cursor_20260605_100000.json`
- Maintain 30-day rolling backup window
- Provide restore command: `agent-sync restore settings cursor 20260605`

---

## 📊 Common Settings Across All Agents

From matrix research, these settings are supported by most agents:

1. ✅ **Model Selection** - 18/24 agents
2. ✅ **Approval/Permission Mode** - 16/24 agents
3. ✅ **Resume/Continue** - 15/24 agents
4. ✅ **Custom Commands** - 14/24 agents
5. ✅ **Telemetry/Privacy** - 12/24 agents
6. 🔲 **Keyboard Shortcuts** - 8/24 agents (HIGH VALUE)
7. 🔲 **Theme Customization** - 7/24 agents (HIGH VALUE)
8. 🔲 **Auto-Save** - 6/24 agents (MEDIUM VALUE)
9. 🔲 **Debug Output** - 6/24 agents (MEDIUM VALUE)
10. 🔲 **Context Window** - 5/24 agents (MEDIUM VALUE)

---

## 🚀 Launch Checklist

- [ ] All schema mappings created
- [ ] Unit tests passing for all agents
- [ ] Integration tests passing
- [ ] Documentation complete
- [ ] User communication plan
- [ ] Backcompat with existing rules/skills/MCP sync
- [ ] Ready for beta release

---

## 📝 Notes

- **Dependencies:** None new; leverages existing `agent-rules-sync` infrastructure
- **Breaking changes:** None; backward compatible
- **User action required:** Optional; users can opt-in via `agent-sync setup`
- **CLI interface:** New scope `agent-sync sync settings` (already exists but needs population)

