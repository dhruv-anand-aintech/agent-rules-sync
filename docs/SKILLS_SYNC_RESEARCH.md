# Skills Sync - Framework Research Summary

Research findings used to implement cross-framework skills synchronization in Agent Rules Sync.

## Framework Skill Storage Locations

### Cursor
- **Global**: `~/.cursor/skills/<skill-name>/SKILL.md`
- **Project**: `.cursor/skills/<skill-name>/SKILL.md` (not synced - project-scoped)
- **Cursor-specific**: `~/.cursor/skills-cursor/<skill-name>/SKILL.md`
- **Migration**: Cursor also scans `.claude/skills/` for Claude compatibility
- **Format**: Folder with mandatory `SKILL.md`, YAML frontmatter, optional assets
- **Source**: [Cursor Docs](https://cursor.com/docs/context/skills)

### Claude Code
- **Global**: `~/.claude/skills/<skill-name>/SKILL.md`
- **Project**: `.claude/skills/<skill-name>/SKILL.md` (not synced)
- **Plugin skills**: `.claude/plugins/cache/*/skills/*` - **excluded** (plugin-managed)
- **Format**: Folder with `SKILL.md`, open Agent Skills standard
- **Source**: [Claude Code Docs](https://code.claude.com/docs/en/skills)

### Codex (OpenAI)
- **User**: `~/.codex/skills/` or `$CODEX_HOME/skills`
- **Shared**: `~/.agents/skills/`
- **Repo**: `.agents/skills/` (not synced)
- **Vendor imports**: `.codex/vendor_imports/skills/` - **excluded** (marketplace-managed)
- **Source**: [OpenAI Codex Docs](https://developers.openai.com/codex/skills/)

### Gemini Antigravity
- **Global**: `~/.gemini/antigravity/skills/`
- **Workspace**: `.agent/skills/` (not synced - project-scoped)
- **Format**: Directory with `SKILL.md`, optional scripts/references
- **Source**: [Antigravity Codelabs](https://codelabs.developers.google.com/getting-started-with-antigravity-skills)

### OpenCode
- **Global**: `~/.config/opencode/skills/`
- **Also checks**: `~/.agents/skills/`, `~/.claude/skills/`
- **Project**: `.opencode/skills/`, `.agents/skills/` (not synced)
- **Format**: Folder with `SKILL.md`, YAML frontmatter
- **Source**: [OpenCode Docs](https://opencode.ai/docs/skills/)

### Shared Path
- **`~/.agents/skills/`**: Used by Codex, OpenCode, and Claude-compatible tools
- Acts as a common location for cross-tool skills

## Update Mechanisms

| Framework | How to Update | When Changes Take Effect |
|-----------|---------------|--------------------------|
| Cursor | Edit files in skill folder | Next conversation / context load |
| Claude | Edit `SKILL.md` or add files | Session restart |
| Codex | Edit in `~/.codex/skills/` | Next invocation |
| Gemini | Edit in `~/.gemini/antigravity/skills/` | Restart or `/learn` refresh |
| OpenCode | Edit in `~/.config/opencode/skills/` | Session restart |

## Backup Strategy

- **Where**: `~/.config/agent-rules-sync/skill_backups/`
- **When**: Before overwriting any skill directory during sync
- **Format**: `{framework}_{skill-name}_{YYYYMMDD}_{HHMMSS}/`
- **Restore**: Copy backup folder back to target framework path
