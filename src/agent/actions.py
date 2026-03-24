"""
Action definitions for the Computer Use agent.

Each action maps to a specific OS interaction (click, type, scroll, etc.).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    """Supported action types."""

    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    KEY = "key"  # Keyboard shortcut (e.g., "cmd+c", "ctrl+alt+del")
    SCROLL = "scroll"
    MOVE = "move"  # Move mouse without clicking
    WAIT = "wait"  # Wait for N seconds
    DONE = "done"  # Task is complete
    FAIL = "fail"  # Task cannot be completed


@dataclass
class Action:
    """A single action to execute on the desktop."""

    type: ActionType
    x: int | None = None  # Screen X coordinate
    y: int | None = None  # Screen Y coordinate
    text: str | None = None  # Text to type or key combo
    amount: int | None = None  # Scroll amount or wait seconds
    reason: str | None = None  # Why this action was chosen

    def to_dict(self) -> dict:
        """Serialize to dict (for conversation history)."""
        d = {"type": self.type.value}
        if self.x is not None:
            d["x"] = self.x
        if self.y is not None:
            d["y"] = self.y
        if self.text is not None:
            d["text"] = self.text
        if self.amount is not None:
            d["amount"] = self.amount
        if self.reason:
            d["reason"] = self.reason
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Action:
        """Deserialize from dict."""
        return cls(
            type=ActionType(d["type"]),
            x=d.get("x"),
            y=d.get("y"),
            text=d.get("text"),
            amount=d.get("amount"),
            reason=d.get("reason"),
        )


def parse_action_response(response: str) -> Action:
    """Parse an LLM response into an Action.

    The LLM is prompted to respond in JSON format:
    {"type": "click", "x": 100, "y": 200, "reason": "Click the search button"}

    Args:
        response: Raw LLM response text.

    Returns:
        Parsed Action object.

    Raises:
        ValueError: If the response cannot be parsed.
    """
    # Try to extract JSON from the response
    text = response.strip()

    # Handle markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    # Find JSON object boundaries
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in response: {response[:200]}")

    json_str = text[start:end]

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in response: {e}") from e

    return Action.from_dict(data)
