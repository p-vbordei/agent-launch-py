from __future__ import annotations

import pytest

from agent_launch.platforms import list_platforms, load_platform_template


def test_loads_hn_template() -> None:
    t = load_platform_template("hn")
    assert t.platform == "hn"
    assert t.length_cap == 2000
    assert t.title_cap == 80
    assert t.output_format == "json"
    assert "Show HN" in t.system
    assert "{{project.name}}" in t.user_template
    assert "revolutionary" in t.anti_examples


def test_loads_x_template() -> None:
    t = load_platform_template("x")
    assert t.platform == "x"
    assert t.length_cap == 280
    assert t.output_format == "thread"
    assert t.min_tweets == 3
    assert t.max_tweets == 5


def test_lists_5_platforms() -> None:
    lst = list_platforms()
    assert sorted(lst) == sorted(["hn", "reddit", "x", "mastodon", "linkedin"])
    assert len(lst) == 5


def test_all_5_templates_load() -> None:
    for p in ("hn", "reddit", "x", "mastodon", "linkedin"):
        t = load_platform_template(p)
        assert len(t.system) > 50
        assert len(t.user_template) > 50
        assert len(t.anti_examples) > 50


def test_throws_on_unknown_platform() -> None:
    with pytest.raises(ValueError):
        load_platform_template("alien")
