"""Tests for the robust JSON extractor (the old non-greedy regex truncated
nested objects)."""
import pytest

from app.agent.tools import extract_json


def test_plain_object():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_plain_array():
    assert extract_json('["x", "y"]') == ["x", "y"]


def test_markdown_fenced():
    text = 'Here you go:\n```json\n{"recommendation": "APPROVE"}\n```\nThanks!'
    assert extract_json(text) == {"recommendation": "APPROVE"}


def test_nested_object_not_truncated():
    # A non-greedy regex would stop at the first closing brace.
    text = 'prose {"outer": {"inner": [1, 2, 3]}, "k": "v"} trailing'
    assert extract_json(text) == {"outer": {"inner": [1, 2, 3]}, "k": "v"}


def test_brace_inside_string_is_ignored():
    text = '{"reasoning": "amount {flagged} for review", "ok": true}'
    assert extract_json(text) == {"reasoning": "amount {flagged} for review", "ok": True}


def test_raises_when_no_json():
    with pytest.raises(ValueError):
        extract_json("no json here at all")
