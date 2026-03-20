"""Tests for AgentSkillsSync - skills sync across agent frameworks."""

import tempfile
from pathlib import Path

import pytest

from agent_skills_sync import AgentSkillsSync


def _create_skill(base_path, skill_name, content="Test skill content"):
    """Create a valid skill directory with SKILL.md."""
    skill_dir = base_path / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {skill_name}\ndescription: {content}\n---\n# {skill_name}\n{content}"
    )
    return skill_dir


def test_list_skills_in_dir():
    """List valid skills in a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        _create_skill(base, "skill-a")
        _create_skill(base, "skill-b")
        (base / "no-skill-md").mkdir()
        (base / "no-skill-md" / "other.txt").write_text("x")

        sync = AgentSkillsSync(config_dir=base / "config")
        sync.master_skills_dir = base
        names = sync._list_skills_in_dir(base)
        assert names == {"skill-a", "skill-b"}


def test_is_valid_skill_dir():
    """Validate skill directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        valid = _create_skill(base, "valid")
        invalid_dir = base / "invalid"
        invalid_dir.mkdir()
        (invalid_dir / "other.txt").write_text("x")

        sync = AgentSkillsSync(config_dir=base / "config")
        assert sync._is_valid_skill_dir(valid) is True
        assert sync._is_valid_skill_dir(invalid_dir) is False


def test_sync_propagates_skill_from_one_framework():
    """Skill in one framework propagates to all others."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = Path(tmpdir) / "config"
        cfg.mkdir()
        cursor_skills = cfg / "cursor" / "skills"
        cursor_skills.mkdir(parents=True)
        claude_skills = cfg / "claude" / "skills"
        codex_skills = cfg / "codex" / "skills"

        sync = AgentSkillsSync(config_dir=cfg)
        sync.frameworks = {
            "cursor": {"name": "Cursor", "path": cursor_skills, "description": ""},
            "claude": {"name": "Claude", "path": claude_skills, "description": ""},
            "codex": {"name": "Codex", "path": codex_skills, "description": ""},
        }
        sync.master_skills_dir = cfg / "skills"
        sync.master_skills_dir.mkdir(exist_ok=True)

        _create_skill(cursor_skills, "my-skill", "Added in Cursor")

        sync.sync(backup_before_write=False)

        assert (sync.master_skills_dir / "my-skill" / "SKILL.md").exists()
        assert (claude_skills / "my-skill" / "SKILL.md").exists()
        assert (codex_skills / "my-skill" / "SKILL.md").exists()


def test_sync_union_from_multiple_sources():
    """Skills from multiple frameworks are unioned and propagated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = Path(tmpdir) / "config"
        cfg.mkdir()
        cursor_skills = cfg / "cursor" / "skills"
        cursor_skills.mkdir(parents=True)
        claude_skills = cfg / "claude" / "skills"
        codex_skills = cfg / "codex" / "skills"

        sync = AgentSkillsSync(config_dir=cfg)
        sync.frameworks = {
            "cursor": {"name": "Cursor", "path": cursor_skills, "description": ""},
            "claude": {"name": "Claude", "path": claude_skills, "description": ""},
            "codex": {"name": "Codex", "path": codex_skills, "description": ""},
        }
        sync.master_skills_dir = cfg / "skills"
        sync.master_skills_dir.mkdir(exist_ok=True)

        _create_skill(cursor_skills, "cursor-skill")
        _create_skill(claude_skills, "claude-skill")

        sync.sync(backup_before_write=False)

        assert (sync.master_skills_dir / "cursor-skill" / "SKILL.md").exists()
        assert (sync.master_skills_dir / "claude-skill" / "SKILL.md").exists()
        assert (codex_skills / "cursor-skill" / "SKILL.md").exists()
        assert (codex_skills / "claude-skill" / "SKILL.md").exists()


def test_sync_handles_skill_with_extra_files():
    """Skill with scripts/references is fully copied."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = Path(tmpdir) / "config"
        cfg.mkdir()
        src_skills = cfg / "src" / "skills"
        src_skills.mkdir(parents=True)
        dst_skills = cfg / "dst" / "skills"

        sync = AgentSkillsSync(config_dir=cfg)
        sync.frameworks = {
            "dst": {"name": "Dst", "path": dst_skills, "description": ""},
        }
        sync.master_skills_dir = cfg / "skills"
        sync.master_skills_dir.mkdir(exist_ok=True)

        skill_dir = _create_skill(src_skills, "rich-skill")
        (skill_dir / "scripts" / "run.sh").parent.mkdir(parents=True)
        (skill_dir / "scripts" / "run.sh").write_text("#!/bin/bash\necho ok")
        (skill_dir / "references" / "api.md").parent.mkdir(parents=True)
        (skill_dir / "references" / "api.md").write_text("# API")

        sync.master_skills_dir = src_skills.parent.parent / "master_skills"
        sync.master_skills_dir.mkdir(exist_ok=True)
        sync._copy_skill(skill_dir, sync.master_skills_dir / "rich-skill")
        sync._copy_skill(
            sync.master_skills_dir / "rich-skill", dst_skills / "rich-skill"
        )

        assert (dst_skills / "rich-skill" / "SKILL.md").exists()
        assert (dst_skills / "rich-skill" / "scripts" / "run.sh").exists()
        assert (dst_skills / "rich-skill" / "references" / "api.md").exists()


def test_skills_changed_detection():
    """Change detection works for skill modifications."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = Path(tmpdir) / "config"
        cfg.mkdir()
        skills_dir = cfg / "skills"
        skills_dir.mkdir()
        _create_skill(skills_dir, "test-skill")

        sync = AgentSkillsSync(config_dir=cfg)
        sync.master_skills_dir = skills_dir

        old_hashes = sync.get_watch_paths_and_hashes()
        assert len(old_hashes) >= 1

        (skills_dir / "test-skill" / "SKILL.md").write_text("modified")
        assert sync.skills_changed(old_hashes) is True


def test_framework_paths_use_home():
    """Default config uses home directory paths."""
    sync = AgentSkillsSync()
    assert ".cursor" in str(sync.frameworks["cursor"]["path"])
    assert ".claude" in str(sync.frameworks["claude"]["path"])
    assert ".codex" in str(sync.frameworks["codex"]["path"]) or "skills" in str(
        sync.frameworks["codex"]["path"]
    )
