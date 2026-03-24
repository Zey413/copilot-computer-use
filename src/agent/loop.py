"""
Core agent control loop.

The main loop: screenshot → vision analysis → action planning → execution.
"""

from __future__ import annotations

import sys
import time
from typing import Any

from ..agent.actions import Action, ActionType, parse_action_response
from ..copilot.client import CopilotClient
from ..executor.base import BaseExecutor
from ..screen.capture import ScreenCapture

SYSTEM_PROMPT = """\
You are a Computer Use agent. You can see the user's screen and control their \
computer to accomplish tasks.

For each screenshot, analyze what you see and decide the next action.

You MUST respond with a single JSON object (no other text):

{
  "type": "<action_type>",
  "x": <x_coordinate>,
  "y": <y_coordinate>,
  "text": "<text_to_type_or_key_combo>",
  "amount": <scroll_amount_or_wait_seconds>,
  "reason": "<brief explanation>"
}

Available action types:
- "click": Click at (x, y)
- "double_click": Double-click at (x, y)
- "right_click": Right-click at (x, y)
- "type": Type text string (set "text" field)
- "key": Press key combo like "cmd+c", "enter", "tab" (set "text" field)
- "scroll": Scroll at (x, y) by amount (positive=up, negative=down)
- "move": Move mouse to (x, y) without clicking
- "wait": Wait for "amount" seconds (use when page is loading)
- "done": Task is complete (set "reason" to describe result)
- "fail": Task cannot be completed (set "reason" to explain why)

Guidelines:
- Coordinates are screen pixels from top-left (0,0)
- Be precise with click coordinates — aim for the center of buttons/links
- After typing, often you need to press "enter" to submit
- Use "wait" if you expect a page to load
- Use "done" when the task objective has been achieved
- Use "fail" if the task is impossible or you're stuck in a loop
"""


class AgentLoop:
    """Core agent control loop."""

    def __init__(
        self,
        client: CopilotClient,
        executor: BaseExecutor,
        screen: ScreenCapture | None = None,
        annotator: Any | None = None,
        max_iterations: int = 50,
        loop_delay: float = 2.0,
    ):
        """Initialize the agent loop.

        Args:
            client: Copilot API client.
            executor: Platform-specific action executor.
            screen: Screen capture instance (auto-created if None).
            annotator: Optional ScreenAnnotator for grid overlay.
            max_iterations: Maximum number of iterations before stopping.
            loop_delay: Delay between iterations (seconds).
        """
        self.client = client
        self.executor = executor
        self.screen = screen or ScreenCapture()
        self.annotator = annotator
        self.max_iterations = max_iterations
        self.loop_delay = loop_delay
        self.history: list[dict[str, Any]] = []

    def run(self, task: str) -> str:
        """Run the agent loop for a given task.

        Args:
            task: Natural language description of the task.

        Returns:
            Final status message.
        """
        print(f"\n{'='*60}")
        print(f"Task: {task}")
        print(f"{'='*60}\n")

        # Initialize conversation with system prompt
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

        for iteration in range(1, self.max_iterations + 1):
            print(f"--- Iteration {iteration}/{self.max_iterations} ---")

            # 1. Capture screenshot
            print("  Capturing screenshot...")
            screenshot_bytes = self.screen.capture()

            # Optional: add grid overlay for better coordinate estimation
            if self.annotator:
                from PIL import Image
                import io

                img = Image.open(io.BytesIO(screenshot_bytes))
                img = self.annotator.add_grid(img)
                screenshot_bytes = self.annotator.to_bytes(img)

            print(f"  Screenshot: {len(screenshot_bytes)} bytes")

            # 2. Send to Copilot Vision API
            print("  Analyzing with Copilot Vision...")
            prompt = self._build_prompt(task, iteration)

            try:
                response = self.client.vision_with_history(
                    messages=self.history,
                    image_bytes=screenshot_bytes,
                    prompt=prompt,
                )
            except Exception as e:
                print(f"  API error: {e}")
                time.sleep(self.loop_delay)
                continue

            print(f"  Response: {response[:200]}...")

            # 3. Parse action
            try:
                action = parse_action_response(response)
            except ValueError as e:
                print(f"  Parse error: {e}")
                # Add error to history and retry
                self.history.append({
                    "role": "user",
                    "content": f"[Screenshot attached] {prompt}",
                })
                self.history.append({
                    "role": "assistant",
                    "content": response,
                })
                self.history.append({
                    "role": "user",
                    "content": "Your response was not valid JSON. Please respond with ONLY a JSON object.",
                })
                time.sleep(self.loop_delay)
                continue

            print(f"  Action: {action.type.value}", end="")
            if action.x is not None:
                print(f" ({action.x}, {action.y})", end="")
            if action.text:
                print(f" text='{action.text}'", end="")
            if action.reason:
                print(f" — {action.reason}", end="")
            print()

            # 4. Update conversation history
            self.history.append({
                "role": "user",
                "content": f"[Screenshot attached] {prompt}",
            })
            self.history.append({
                "role": "assistant",
                "content": response,
            })

            # 5. Check terminal actions
            if action.type == ActionType.DONE:
                msg = f"Task completed: {action.reason}"
                print(f"\n  {msg}")
                return msg

            if action.type == ActionType.FAIL:
                msg = f"Task failed: {action.reason}"
                print(f"\n  {msg}")
                return msg

            # 6. Execute action
            print("  Executing...")
            try:
                self.executor.execute(action)
            except Exception as e:
                print(f"  Execution error: {e}")

            # 7. Delay before next iteration
            time.sleep(self.loop_delay)

            # Prune history to avoid token limits (keep last 10 exchanges)
            if len(self.history) > 22:  # system + 10 * (user + assistant)
                self.history = [self.history[0]] + self.history[-20:]

        return f"Reached maximum iterations ({self.max_iterations})"

    def _build_prompt(self, task: str, iteration: int) -> str:
        """Build the prompt for the current iteration."""
        if iteration == 1:
            return (
                f"Task: {task}\n\n"
                "This is the current state of the screen. "
                "What is the first action to take?"
            )
        return (
            f"Task: {task}\n\n"
            "This is the updated screen after the previous action. "
            "What is the next action? If the task is complete, respond with 'done'."
        )
