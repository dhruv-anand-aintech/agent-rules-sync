# Agent Configuration File Reload Behavior

This document explains when and how each AI coding assistant reads its configuration files after they are updated by Agent Rules Sync.

## Summary Table

| Agent | Config File | Reload Behavior | Timing | Restart Required? |
|-------|-------------|-----------------|--------|-------------------|
| **Claude Code** | `~/.claude/CLAUDE.md` | At startup only | Session start | ✓ Yes |
| **Cursor** | `~/.cursor/rules/global.mdc` | Per-conversation context load | Each conversation | Maybe* |
| **Gemini Antigravity** | `~/.gemini/GEMINI.md` | Manual reload only | Manual `/memory refresh` | ✓ Yes |
| **OpenCode** | `~/.config/opencode/AGENTS.md` | At session startup | Session start | ✓ Yes |

*Cursor may ignore rules after several messages due to context window optimization.

---

## Detailed Breakdown

### 1. Claude Code (`~/.claude/CLAUDE.md`)

**How it works:**
- Loads CLAUDE.md **at startup/session start** only
- Content is treated as persistent context/instructions for the session

**Reload behavior:**
- ❌ **No automatic reload** - Changes to CLAUDE.md do NOT take effect during an active session
- Changes only apply to **new sessions** after restarting Claude Code

**Recommendation for Agent Rules Sync:**
```bash
# After syncing, users should:
1. Close Claude Code
2. Start a new session
3. Changes now apply
```

**Source:** [Using CLAUDE.MD files | Claude](https://claude.com/blog/using-claude-md-files)

---

### 2. Cursor (`~/.cursor/rules/global.mdc`)

**How it works:**
- Uses `.mdc` (Markdown with Code) format for rules
- Rules are loaded per conversation/context

**Reload behavior:**
- ⚠️ **Per-conversation loading** - New rules apply in new conversations
- **Context window issue**: After a few messages in a conversation, Cursor may ignore rules due to context window optimization (recency wins over rules)
- May require explicit reminder comments like "remember the rules" to keep them in focus

**Recommendation for Agent Rules Sync:**
```bash
# After syncing, users should:
1. Start a new conversation/session
2. Rules apply to new chats
3. Consider restating rules periodically in long conversations
```

**Notes:**
- Rules file is now in `.mdc` format (improved over earlier text format)
- Multiple `.mdc` files can coexist in `~/.cursor/rules/` directory
- Project-level `.cursor/rules/global.mdc` can override global rules

**Sources:**
- [Rules | Cursor Docs](https://cursor.com/docs/context/rules)
- [Best Practices for MDC rules | Cursor Forum](https://forum.cursor.com/t/my-best-practices-for-mdc-rules-and-troubleshooting/50526)

---

### 3. Gemini Antigravity (`~/.gemini/GEMINI.md`)

**How it works:**
- Stores global context/instructions for Gemini CLI and Antigravity IDE
- Both tools share the same file (can cause conflicts)

**Reload behavior:**
- ❌ **Manual reload only** - No automatic file watching
- Requires explicit command to reload: `/memory refresh`
- `/memory add <text>` appends to the file directly

**Recommendation for Agent Rules Sync:**
```bash
# After syncing, users should:
1. Run /memory refresh in Gemini Antigravity
2. Or restart Gemini CLI/Antigravity session
3. Then changes apply
```

**Important notes:**
- ⚠️ Both **Antigravity IDE** and **Gemini CLI** write to the same file (~/.gemini/GEMINI.md)
- This can cause conflicts if both tools are used simultaneously
- Configuration setting: `loadFromIncludeDirectories` controls file discovery

**Source:** [Gemini CLI configuration | Gemini CLI](https://geminicli.com/docs/get-started/configuration/)

---

### 4. OpenCode (`~/.config/opencode/AGENTS.md`)

**How it works:**
- Loads from multiple locations (global and project-level)
- Supports hierarchical configuration (closest file takes precedence)
- Can place project-specific AGENTS.md in any directory level

**Reload behavior:**
- ❌ **At session startup only** - Loaded when starting new session
- Changes apply to new sessions, not current sessions
- File watcher can be configured to ignore certain patterns

**Recommendation for Agent Rules Sync:**
```bash
# After syncing, users should:
1. Restart OpenCode or start a new session
2. Changes now apply
```

**Notes:**
- Global rules: `~/.config/opencode/AGENTS.md`
- Project rules: `./AGENTS.md` in any project directory
- Closest AGENTS.md file in directory tree takes precedence
- Community has requested better auto-reload detection in monorepos

**Sources:**
- [Rules | OpenCode](https://opencode.ai/docs/rules/)
- [Agents | OpenCode](https://opencode.ai/docs/agents/)

---

## Impact on Agent Rules Sync

Based on this research:

### What Works Well ✓
- Agent Rules Sync successfully syncs files across all agents
- Changes are persistent and available after restart/new session
- Merging and deduplication work reliably

### What Requires User Action ⚠️
| Agent | Required Action |
|-------|-----------------|
| Claude Code | Restart application or new session |
| Cursor | Start new conversation |
| Gemini | Run `/memory refresh` or restart |
| OpenCode | Restart or new session |

### Recommendations for Users

**In the README/documentation, add a note:**

```markdown
## After Sync - Making Changes Take Effect

Since most agents load configuration at startup:

1. **Claude Code**: Restart the application or start a new session
2. **Cursor**: Changes apply to new conversations automatically
3. **Gemini Antigravity**: Run `/memory refresh` command in the IDE
4. **OpenCode**: Restart or start a new session

Agent Rules Sync automatically keeps files synchronized.
Users just need to restart their agent for changes to take effect.
```

---

## Technical Implementation Notes

For future improvements to Agent Rules Sync:

1. **Hotfile Watching**: Consider adding file system notifications (fsnotify) if needed in future
2. **Restart Detection**: Could potentially detect when agents restart and auto-sync
3. **Gemini Integration**: Could provide a helper command to run `/memory refresh` automatically
4. **Cursor Optimization**: Long conversations may need periodic rule reinforcement

---

## References

- [Claude Code: Using CLAUDE.MD files](https://claude.com/blog/using-claude-md-files)
- [Cursor Documentation: Rules](https://cursor.com/docs/context/rules)
- [Gemini CLI: Configuration](https://geminicli.com/docs/get-started/configuration/)
- [OpenCode: Rules Documentation](https://opencode.ai/docs/rules/)
- [Cursor Forum: MDC Rules Best Practices](https://forum.cursor.com/t/my-best-practices-for-mdc-rules-and-troubleshooting/50526)
