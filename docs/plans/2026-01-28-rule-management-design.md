# Rule Management Design: Removal & Agent-Specific Rules

**Date:** 2026-01-28  
**Status:** Approved  

## Overview

Enable two new capabilities:
1. **Rule deletion:** Remove rules by deleting them from the master file; they disappear from all agents on next sync
2. **Agent-specific rules:** Define rules that stay local to one agent under special headings

## Master File Structure

Master file (`~/.config/agent-rules-sync/RULES.md`) uses sections:

```markdown
# Shared Rules
- rule 1 (syncs to all agents)
- rule 2

## Claude Code Specific
- claude-specific rule

## Cursor Specific
- cursor-specific rule

## Gemini Specific
- gemini-specific rule

## OpenCode Specific
- opencode-specific rule
```

**Key points:**
- "Shared Rules" section syncs to all agent files
- Agent-specific sections only sync to their corresponding agent
- Deleted rules simply don't appear in next sync (backups preserve history)

## Agent File Format

Each agent file mirrors the master structure:

```markdown
# Shared Rules
- rule 1
- rule 2

## Claude Code Specific
- claude-specific rule
```

Users edit their agent files directly:
- Add/remove rules in "Shared Rules" → syncs everywhere
- Add/remove rules under their agent's section → stays local
- Ignore other agent sections (e.g., Cursor section in Claude file)

## Sync Algorithm

### Reading from Agent Files

1. Parse "Shared Rules" section (before first `##` heading)
2. Parse agent-specific section (under `## [Agent Name] Specific`)
3. Extract all rules starting with `-`
4. Merge shared rules into master's "Shared Rules" (union, deduplicate)
5. Merge agent rules into master's corresponding agent section (union, deduplicate)

### Writing to Agent Files

1. Read master file
2. Extract "Shared Rules" section
3. Extract that agent's section (e.g., `## Claude Code Specific`)
4. Write agent file with both sections combined
5. Do not write other agent sections

### Deletion & Conflicts

- **Deletion:** Simply remove rule line from master; next sync removes it from all agents
- **Deduplication:** Union-based merge keeps all rules from all sources, with duplicates removed
- **Conflict:** Same rule in shared + agent-specific? Deduplicate (keep one)

## Implementation Changes

### New Parser Methods

```python
_extract_shared_rules(content)        # Extract "# Shared Rules" section
_extract_agent_rules(content, agent)  # Extract agent-specific section
_parse_sections(content)              # Split file into shared + agent sections
```

### Updated Core Logic

1. **`_merge_rules()`** 
   - Track shared vs agent-specific rules separately
   - Merge shared rules across all sources
   - Merge each agent's rules only with itself

2. **`sync()`**
   - Read master → extract shared + each agent section
   - Read each agent file → extract shared + that agent's section
   - Merge appropriately by section
   - Write master with all sections
   - Write each agent file with shared + its section only

3. **Master file initialization**
   - Create with "# Shared Rules" + all agent-specific headings
   - No longer a flat list

## Benefits

✓ Rule deletion is intuitive (just delete the line)  
✓ Agent-specific rules have clear, dedicated space  
✓ Shared rules still sync everywhere by default  
✓ Backups preserve deleted rules for recovery  
✓ Master file is always the source of truth  

