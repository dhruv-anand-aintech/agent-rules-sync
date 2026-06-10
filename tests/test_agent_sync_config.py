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
