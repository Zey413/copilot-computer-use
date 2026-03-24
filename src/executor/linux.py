"""
Linux action executor using pyautogui with optional xdotool fallback.

Works on X11 and Wayland (with limitations on Wayland).
"""

from __future__ import annotations

import shutil
import subprocess

import pyautogui

from .base import BaseExecutor

# Safety settings
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


class LinuxExecutor(BaseExecutor):
    """Execute desktop actions on Linux using pyautogui + xdotool."""

    def __init__(
        self,
        action_delay: float = 0.5,
        mouse_duration: float = 0.3,
        prefer_xdotool: bool = False,
    ):
        """Initialize Linux executor.

        Args:
            action_delay: Delay after each action (seconds).
            mouse_duration: Duration for mouse movements (seconds).
            prefer_xdotool: If True, use xdotool for typing when available.
                           xdotool handles Unicode better than pyautogui on X11.
        """
        super().__init__(action_delay=action_delay, mouse_duration=mouse_duration)
        self._has_xdotool = shutil.which("xdotool") is not None
        self._prefer_xdotool = prefer_xdotool and self._has_xdotool

        if prefer_xdotool and not self._has_xdotool:
            print("Warning: xdotool not found, falling back to pyautogui")

    def click(self, x: int, y: int) -> None:
        pyautogui.click(x, y, duration=self.mouse_duration)

    def double_click(self, x: int, y: int) -> None:
        pyautogui.doubleClick(x, y, duration=self.mouse_duration)

    def right_click(self, x: int, y: int) -> None:
        pyautogui.rightClick(x, y, duration=self.mouse_duration)

    def type_text(self, text: str) -> None:
        """Type text string.

        Uses xdotool for better Unicode support on X11 when available
        and prefer_xdotool is set. Falls back to pyautogui.
        """
        if self._prefer_xdotool:
            try:
                subprocess.run(
                    ["xdotool", "type", "--clearmodifiers", "--", text],
                    check=True,
                    timeout=10,
                )
                return
            except (subprocess.SubprocessError, FileNotFoundError):
                pass  # Fall back to pyautogui

        pyautogui.write(text, interval=0.02)

    def press_key(self, key_combo: str) -> None:
        """Press a key combination.

        Supports modifiers: ctrl, alt, shift, super/meta.
        Examples: "ctrl+c", "alt+tab", "super+l"
        """
        keys = key_combo.lower().split("+")

        if self._prefer_xdotool and len(keys) > 1:
            # xdotool handles complex key combos better on X11
            try:
                xdotool_keys = "+".join(self._map_key_xdotool(k) for k in keys)
                subprocess.run(
                    ["xdotool", "key", "--clearmodifiers", xdotool_keys],
                    check=True,
                    timeout=5,
                )
                return
            except (subprocess.SubprocessError, FileNotFoundError):
                pass

        # pyautogui fallback
        if len(keys) == 1:
            pyautogui.press(self._map_key_pyautogui(keys[0]))
        else:
            mapped = [self._map_key_pyautogui(k) for k in keys]
            pyautogui.hotkey(*mapped)

    def scroll(self, x: int | None, y: int | None, amount: int) -> None:
        if x is not None and y is not None:
            pyautogui.moveTo(x, y, duration=self.mouse_duration)
        pyautogui.scroll(amount)

    def move_mouse(self, x: int, y: int) -> None:
        pyautogui.moveTo(x, y, duration=self.mouse_duration)

    @staticmethod
    def _map_key_pyautogui(key: str) -> str:
        """Map common key names to pyautogui names."""
        mapping = {
            "ctrl": "ctrl",
            "alt": "alt",
            "shift": "shift",
            "super": "winleft",
            "meta": "winleft",
            "cmd": "winleft",  # Map cmd to super on Linux
            "enter": "return",
            "esc": "escape",
            "tab": "tab",
            "space": "space",
            "backspace": "backspace",
            "delete": "delete",
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            "home": "home",
            "end": "end",
            "pageup": "pageup",
            "pagedown": "pagedown",
        }
        return mapping.get(key, key)

    @staticmethod
    def _map_key_xdotool(key: str) -> str:
        """Map common key names to xdotool names."""
        mapping = {
            "ctrl": "ctrl",
            "alt": "alt",
            "shift": "shift",
            "super": "super",
            "meta": "super",
            "cmd": "super",
            "enter": "Return",
            "esc": "Escape",
            "tab": "Tab",
            "space": "space",
            "backspace": "BackSpace",
            "delete": "Delete",
            "up": "Up",
            "down": "Down",
            "left": "Left",
            "right": "Right",
        }
        return mapping.get(key, key)
