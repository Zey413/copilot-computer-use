"""
Abstract base executor for desktop actions.

Platform-specific implementations (macOS, Linux) inherit from this.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from ..agent.actions import Action, ActionType


class BaseExecutor(ABC):
    """Abstract base class for action executors."""

    def __init__(self, action_delay: float = 0.5, mouse_duration: float = 0.3):
        """Initialize executor.

        Args:
            action_delay: Delay after each action (seconds).
            mouse_duration: Duration for mouse movements (seconds).
        """
        self.action_delay = action_delay
        self.mouse_duration = mouse_duration

    def execute(self, action: Action) -> None:
        """Execute an action.

        Args:
            action: The action to execute.
        """
        match action.type:
            case ActionType.CLICK:
                self.click(action.x, action.y)
            case ActionType.DOUBLE_CLICK:
                self.double_click(action.x, action.y)
            case ActionType.RIGHT_CLICK:
                self.right_click(action.x, action.y)
            case ActionType.TYPE:
                self.type_text(action.text)
            case ActionType.KEY:
                self.press_key(action.text)
            case ActionType.SCROLL:
                self.scroll(action.x, action.y, action.amount)
            case ActionType.MOVE:
                self.move_mouse(action.x, action.y)
            case ActionType.WAIT:
                time.sleep(action.amount or 1)
            case ActionType.DONE | ActionType.FAIL:
                pass  # No OS action needed

        # Post-action delay
        if action.type not in (ActionType.DONE, ActionType.FAIL, ActionType.WAIT):
            time.sleep(self.action_delay)

    @abstractmethod
    def click(self, x: int, y: int) -> None:
        """Click at coordinates."""

    @abstractmethod
    def double_click(self, x: int, y: int) -> None:
        """Double-click at coordinates."""

    @abstractmethod
    def right_click(self, x: int, y: int) -> None:
        """Right-click at coordinates."""

    @abstractmethod
    def type_text(self, text: str) -> None:
        """Type text string."""

    @abstractmethod
    def press_key(self, key_combo: str) -> None:
        """Press a key combination (e.g., 'cmd+c')."""

    @abstractmethod
    def scroll(self, x: int | None, y: int | None, amount: int) -> None:
        """Scroll at position."""

    @abstractmethod
    def move_mouse(self, x: int, y: int) -> None:
        """Move mouse to coordinates."""
