# Rule Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Enable rule deletion and agent-specific rules by restructuring master file with "Shared Rules" + agent-specific sections, and updating sync logic to handle bidirectional rule flow.

**Architecture:** Parser methods extract shared vs agent-specific rules from files, sync merges rules by section, and rebuild writes both shared and agent-specific sections to each agent file.

**Tech Stack:** Python standard library only (pathlib, hashlib, datetime)

---

## Task 1: Add Section Parsing Methods

**Files:**
- Modify: `agent_rules_sync.py:95-102` (replace _merge_rules with new methods)

**Step 1: Write failing tests**

Create test_agent_rules_sync.py

**Step 2: Run tests to verify they fail**

Run: python -m pytest test_agent_rules_sync.py -v
Expected: All 4 tests FAIL with AttributeError

**Step 3: Implement the parser methods**

Replace lines 95-102 with parser methods for _extract_shared_rules, _extract_agent_rules, _get_agent_heading, _build_file_content

**Step 4: Run tests to verify they pass**

Run: python -m pytest test_agent_rules_sync.py -v
Expected: All 4 tests PASS

**Step 5: Commit**

git add test_agent_rules_sync.py agent_rules_sync.py
git commit -m "feat: add section parsing methods for shared and agent-specific rules"

---

## Task 2: Update Master File Initialization

**Files:**
- Modify: agent_rules_sync.py:104-118

**Step 1: Write failing test for master file sections**

Test that _ensure_master_exists creates all agent-specific sections

**Step 2: Run test to verify it fails**

Expected: FAIL - master file doesn't have all sections

**Step 3: Update _ensure_master_exists method**

Build master with "# Shared Rules" section plus all agent-specific sections

**Step 4: Run test to verify it passes**

Expected: PASS

**Step 5: Commit**

git add agent_rules_sync.py
git commit -m "feat: initialize master file with shared and agent-specific sections"

---

## Task 3: Rewrite sync() Method

**Files:**
- Modify: agent_rules_sync.py:120-165

**Step 1: Write failing tests**

- test_sync_merges_shared_rules
- test_sync_keeps_agent_specific_rules  
- test_sync_does_not_cross_pollinate_agent_rules

**Step 2: Run tests to verify they fail**

Expected: All 3 FAIL

**Step 3: Rewrite sync() method**

New logic:
1. Read master, extract shared and agent sections
2. Read all agents, merge their shared + agent-specific rules
3. Rebuild master with all sections
4. Write each agent file with shared + their section only

**Step 4: Run tests to verify they pass**

Expected: All 3 PASS

**Step 5: Commit**

git add agent_rules_sync.py
git commit -m "feat: rewrite sync to handle shared and agent-specific rule sections"

---

## Task 4: Add Integration Tests

**Files:**
- Create: test_agent_rules_sync_integration.py

**Step 1: Write integration tests**

- test_full_workflow_shared_rules
- test_full_workflow_agent_specific
- test_full_workflow_rule_deletion

**Step 2: Run tests to verify they pass**

Expected: All 3 PASS

**Step 3: Commit**

git add test_agent_rules_sync_integration.py
git commit -m "test: add integration tests for shared and agent-specific rules"

---

## Task 5: Update Documentation

**Files:**
- Modify: README.md (add section explaining new feature)

**Step 1: Add documentation section**

Insert after "## Usage" explaining:
- How shared rules work
- How agent-specific rules work
- How to delete rules

**Step 2: Verify documentation**

cat README.md | grep -A 20 "Shared vs Agent-Specific"

**Step 3: Commit**

git add README.md
git commit -m "docs: add section for shared vs agent-specific rules"

---

## Task 6: Manual Testing

**Files:**
- None (manual testing only)

**Step 1: Start daemon in watch mode**

agent-rules-sync stop
python agent_rules_sync.py watch

**Step 2: Test shared rule sync**

Add rule to ~/.claude/CLAUDE.md, verify it appears in cursor

**Step 3: Test agent-specific rule**

Add rule under Claude Code Specific section, verify it does NOT appear in cursor

**Step 4: Test rule deletion**

Delete rule from master, verify it disappears from all agents

**Step 5: Stop daemon**

Press Ctrl+C

---

## Summary

Total: 11 unit tests, 3 integration tests, 5 commits

Ready to start Task 1: implementing parser methods
