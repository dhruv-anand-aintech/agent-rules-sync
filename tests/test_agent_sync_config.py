import json

from agent_sync_config import DEFAULT_CONFIG, load_config


def test_load_config_ignores_invalid_component_values(tmp_path):
    (tmp_path / "sync_config.json").write_text(json.dumps({
        "mode": "sideways",
        "components": {
            "rules": {"direction": "destroy", "enabled": "yes"},
            "skills": {"direction": "pull", "enabled": False},
            "settings": {"direction": "bidirectional", "enabled": True},
        },
    }))

    cfg = load_config(tmp_path)

    assert cfg.mode == DEFAULT_CONFIG["mode"]
    assert cfg.direction("rules") == DEFAULT_CONFIG["components"]["rules"]["direction"]
    assert cfg.enabled("rules") is DEFAULT_CONFIG["components"]["rules"]["enabled"]
    assert cfg.direction("skills") == "pull"
    assert cfg.enabled("skills") is False
    assert cfg.direction("settings") == DEFAULT_CONFIG["components"]["settings"]["direction"]
    assert cfg.enabled("settings") is True


def test_load_config_accepts_valid_partial_overrides(tmp_path):
    (tmp_path / "sync_config.json").write_text(json.dumps({
        "mode": "per_component",
        "components": {
            "mcp": {"direction": "push"},
            "hooks": {"enabled": False},
        },
    }))

    cfg = load_config(tmp_path)

    assert cfg.mode == "per_component"
    assert cfg.direction("mcp") == "push"
    assert cfg.enabled("mcp") is True
    assert cfg.direction("hooks") == "push"
    assert cfg.enabled("hooks") is False


def test_load_config_ignores_non_object_components_without_discarding_valid_mode(tmp_path):
    (tmp_path / "sync_config.json").write_text(json.dumps({
        "mode": "per_component",
        "components": ["rules"],
    }))

    cfg = load_config(tmp_path)

    assert cfg.mode == "per_component"
    assert cfg.direction("rules") == DEFAULT_CONFIG["components"]["rules"]["direction"]
    assert cfg.enabled("rules") is DEFAULT_CONFIG["components"]["rules"]["enabled"]


def test_load_config_merges_skill_target_overrides(tmp_path):
    (tmp_path / "sync_config.json").write_text(json.dumps({
        "skill_targets": {
            "agents": False,
            "repo:example": False,
            "codex": "no",
            "custom": {
                "enabled": False,
                "path": "~/custom/skills",
                "name": "Custom Skills",
                "description": "Custom path",
            },
        },
    }))

    cfg = load_config(tmp_path)

    assert cfg.skill_target_enabled("agents") is False
    assert cfg.skill_target_enabled("repo:example") is False
    assert cfg.skill_target_enabled("codex") is True
    assert cfg.skill_target_enabled("new-target") is True
    assert cfg.skill_target_enabled("custom") is False
    assert cfg.skill_target_configs()["custom"]["path"] == "~/custom/skills"
