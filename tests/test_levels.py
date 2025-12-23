import os
import yaml

import run


def test_levels_yaml_loads():
    """levels.yaml should load and contain expected structure."""
    cfg = run.load_levels_config()
    assert isinstance(cfg, dict)
    assert "levels" in cfg
    assert "ball01" in cfg["levels"]


def test_full_label_lookup():
    assert run.get_level_label("ball01") == "Tea with Granny"
    assert run.get_level_label("ball02") == "Shopping with Granny"


def test_short_label_lookup():
    assert run.get_level_short_label("ball01") == "Tea"
    assert run.get_level_short_label("ball03") == "Annoyed"


def test_duration_lookup():
    # Values come from data/levels.yaml
    assert run.get_level_duration("ball01") == 10
    assert run.get_level_duration("ball04") == 20


def test_level_up_target_lookup():
    assert run.get_level_up_target("ball01") == 3
    assert run.get_level_up_target("ball04") == 3


def test_unknown_level_fallbacks():
    assert run.get_level_label("unknown") == "unknown"
    assert run.get_level_short_label("unknown") == "unknown"
    assert run.get_level_duration("unknown", default_seconds=15) == 15
    assert run.get_level_up_target("unknown", default_target=2) == 2