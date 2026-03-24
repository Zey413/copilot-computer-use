"""Tests for action parsing and serialization."""

from __future__ import annotations

import pytest

from src.agent.actions import Action, ActionType, parse_action_response


class TestActionFromDict:
    """Test Action.from_dict() deserialization."""

    def test_click_action(self):
        action = Action.from_dict({"type": "click", "x": 100, "y": 200})
        assert action.type == ActionType.CLICK
        assert action.x == 100
        assert action.y == 200

    def test_type_action(self):
        action = Action.from_dict({"type": "type", "text": "hello world"})
        assert action.type == ActionType.TYPE
        assert action.text == "hello world"

    def test_key_action(self):
        action = Action.from_dict({"type": "key", "text": "cmd+c"})
        assert action.type == ActionType.KEY
        assert action.text == "cmd+c"

    def test_scroll_action(self):
        action = Action.from_dict({"type": "scroll", "x": 50, "y": 50, "amount": -3})
        assert action.type == ActionType.SCROLL
        assert action.amount == -3

    def test_done_action(self):
        action = Action.from_dict({"type": "done", "reason": "Task completed"})
        assert action.type == ActionType.DONE
        assert action.reason == "Task completed"

    def test_fail_action(self):
        action = Action.from_dict({"type": "fail", "reason": "Cannot find element"})
        assert action.type == ActionType.FAIL
        assert action.reason == "Cannot find element"

    def test_wait_action(self):
        action = Action.from_dict({"type": "wait", "amount": 5})
        assert action.type == ActionType.WAIT
        assert action.amount == 5

    def test_optional_fields_default_none(self):
        action = Action.from_dict({"type": "click", "x": 0, "y": 0})
        assert action.text is None
        assert action.amount is None
        assert action.reason is None


class TestActionToDict:
    """Test Action.to_dict() serialization."""

    def test_roundtrip(self):
        original = Action(type=ActionType.CLICK, x=100, y=200, reason="test")
        d = original.to_dict()
        restored = Action.from_dict(d)
        assert restored.type == original.type
        assert restored.x == original.x
        assert restored.y == original.y
        assert restored.reason == original.reason

    def test_omits_none_fields(self):
        action = Action(type=ActionType.DONE, reason="done")
        d = action.to_dict()
        assert "x" not in d
        assert "y" not in d
        assert "text" not in d
        assert "amount" not in d
        assert d["type"] == "done"
        assert d["reason"] == "done"


class TestParseActionResponse:
    """Test parse_action_response() with various LLM output formats."""

    def test_clean_json(self):
        response = '{"type": "click", "x": 150, "y": 300, "reason": "Click button"}'
        action = parse_action_response(response)
        assert action.type == ActionType.CLICK
        assert action.x == 150
        assert action.y == 300

    def test_json_in_markdown_code_block(self):
        response = '''Here's my action:
```json
{"type": "type", "text": "hello"}
```'''
        action = parse_action_response(response)
        assert action.type == ActionType.TYPE
        assert action.text == "hello"

    def test_json_in_generic_code_block(self):
        response = '''```
{"type": "key", "text": "enter"}
```'''
        action = parse_action_response(response)
        assert action.type == ActionType.KEY
        assert action.text == "enter"

    def test_json_with_surrounding_text(self):
        response = 'I will click the button. {"type": "click", "x": 50, "y": 60} That should work.'
        action = parse_action_response(response)
        assert action.type == ActionType.CLICK
        assert action.x == 50

    def test_done_response(self):
        response = '{"type": "done", "reason": "Successfully searched for weather"}'
        action = parse_action_response(response)
        assert action.type == ActionType.DONE
        assert "weather" in action.reason

    def test_no_json_raises_error(self):
        with pytest.raises(ValueError, match="No JSON object found"):
            parse_action_response("I don't know what to do")

    def test_invalid_json_raises_error(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_action_response("{type: click, x: 100}")

    def test_invalid_action_type_raises_error(self):
        with pytest.raises(ValueError):
            parse_action_response('{"type": "fly_to_moon"}')

    def test_whitespace_handling(self):
        response = '  \n  {"type": "wait", "amount": 3}  \n  '
        action = parse_action_response(response)
        assert action.type == ActionType.WAIT
        assert action.amount == 3


class TestActionType:
    """Test ActionType enum."""

    def test_all_types_exist(self):
        expected = [
            "click", "double_click", "right_click", "type", "key",
            "scroll", "move", "wait", "done", "fail",
        ]
        for name in expected:
            assert ActionType(name) is not None

    def test_terminal_actions(self):
        """done and fail should be recognized as terminal."""
        terminal = {ActionType.DONE, ActionType.FAIL}
        assert ActionType.DONE in terminal
        assert ActionType.FAIL in terminal
        assert ActionType.CLICK not in terminal
