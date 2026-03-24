"""
macOS action executor using pyautogui.
"""

from __future__ import annotations

import pyautogui

from .base import BaseExecutor


# Safety: prevent pyautogui from moving to (0,0) on error
pyautogui.FAILSAFE = True
# Disable default pause (we handle our own delays)
pyautogui.PAUSE = 0.1


class MacOSExecutor(BaseExecutor):
    """Execute desktop actions on macOS using pyautogui."""

    def click(self, x: int, y: int) -> None:
        pyautogui.click(x, y, duration=self.mouse_duration)

    def double_click(self, x: int, y: int) -> None:
        pyautogui.doubleClick(x, y, duration=self.mouse_duration)

    def right_click(self, x: int, y: int) -> None:
        pyautogui.rightClick(x, y, duration=self.mouse_duration)

    def type_text(self, text: str) -> None:
        pyautogui.write(text, interval=0.02)

    def press_key(self, key_combo: str) -> None:
        """Press a key combination like 'cmd+c' or 'enter'.

        Supports modifiers: cmd, ctrl, alt, shift.
        """
        keys = key_combo.lower().split("+")
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            # Map common names to pyautogui names
            key_map = {
                "cmd": "command",
                "ctrl": "ctrl",
                "alt": "option",
                "shift": "shift",
                "enter": "return",
                "esc": "escape",
                "tab": "tab",
                "space": "space",
                "backspace": "backspace",
                "delete": "delete",
            }
            mapped = [key_map.get(k, k) for k in keys]
            pyautogui.hotkey(*mapped)

    def scroll(self, x: int | None, y: int | None, amount: int) -> None:
        if x is not None and y is not None:
            pyautogui.moveTo(x, y, duration=self.mouse_duration)
        pyautogui.scroll(amount)

    def move_mouse(self, x: int, y: int) -> None:
        pyautogui.moveTo(x, y, duration=self.mouse_duration)
