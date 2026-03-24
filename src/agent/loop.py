"""
Core agent control loop.

The main loop: screenshot → vision analysis → action planning → execution.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from ..agent.actions import Action, ActionType, parse_action_response
from ..copilot.client import CopilotClient, RateLimitError
from ..executor.base import BaseExecutor
from ..screen.capture import ScreenCapture

SYSTEM_PROMPT = """\
You are a Computer Use agent. You control the user's desktop to accomplish tasks.
You receive screenshots and must decide the next action.

RESPONSE FORMAT: You MUST respond with ONLY a JSON object, nothing else:

{"type": "<action>", "x": <x>, "y": <y>, "text": "<str>", "amount": <int>, "reason": "<why>"}

ACTIONS:
- "click" (x, y): Left-click at coordinates
- "double_click" (x, y): Double-click
- "right_click" (x, y): Right-click / context menu
- "type" (text): Type a text string
- "key" (text): Press key combo, e.g. "cmd+c", "enter", "ctrl+a", "alt+tab"
- "scroll" (x, y, amount): Scroll wheel. amount>0 = up, amount<0 = down
- "move" (x, y): Move mouse without clicking
- "wait" (amount): Wait N seconds (for loading)
- "done" (reason): Task is complete — explain what was accomplished
- "fail" (reason): Task is impossible — explain why

COORDINATE RULES:
- Origin (0, 0) is the TOP-LEFT corner of the screen
- X increases rightward, Y increases downward
- Aim for the CENTER of clickable elements (buttons, links, icons)
- If a red coordinate grid overlay is visible, use the labeled numbers as reference
  points to estimate positions more accurately

STRATEGY:
1. First, describe what you see on screen (internally — don't output this)
2. Identify which UI element you need to interact with
3. Estimate its center coordinates
4. Choose the appropriate action
5. After typing text, usually press "enter" to submit
6. After clicking, wait for the UI to respond before next action
7. If you see the same screen twice with no change, try a different approach
8. If stuck for 3+ iterations, use "fail" with explanation
"""

SYSTEM_PROMPT_GRID_ADDENDUM = """
NOTE: The screenshot has a red coordinate grid overlay with labeled numbers.
Use these grid labels to estimate positions more precisely. For example, if a
button appears to be at the intersection of grid line 400 (horizontal) and
grid line 300 (vertical), click at approximately (400, 300).
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
        # Show model cost info
        model = self.client.config.vision_model
        cost = self.client.get_model_cost(model)
        cost_label = "FREE" if cost == 0 else f"{cost}x premium"

        print(f"\n{'='*60}")
        print(f"  Task: {task}")
        print(f"  Model: {model} ({cost_label})")
        if self.annotator:
            print(f"  Grid: enabled")
        print(f"  Max iterations: {self.max_iterations}")
        print(f"{'='*60}\n")

        # Initialize conversation with system prompt
        prompt = SYSTEM_PROMPT
        if self.annotator:
            prompt += SYSTEM_PROMPT_GRID_ADDENDUM
        self.history = [{"role": "system", "content": prompt}]

        # Screenshot change detection
        last_screenshot_hash = None
        unchanged_count = 0
        max_unchanged = 3  # Warn after N identical screenshots

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

            # Check if screenshot changed from last iteration
            current_hash = hashlib.md5(screenshot_bytes).hexdigest()
            if current_hash == last_screenshot_hash:
                unchanged_count += 1
                if unchanged_count >= max_unchanged:
                    print(f"  ⚠️  Screen unchanged for {unchanged_count} iterations!")
            else:
                unchanged_count = 0
            last_screenshot_hash = current_hash

            # 2. Send to Copilot Vision API
            print("  Analyzing with Copilot Vision...")
            prompt = self._build_prompt(task, iteration, unchanged_count)

            try:
                response = self.client.vision_with_history(
                    messages=self.history,
                    image_bytes=screenshot_bytes,
                    prompt=prompt,
                )
            except RateLimitError as e:
                print(f"  🔴 Rate limit exhausted: {e}")
                if e.retry_after:
                    print(f"     Server suggests waiting {e.retry_after}s")
                print(f"     (Client already retried {self.client.max_retries} times)")
                self._print_stats(iteration)
                return f"Stopped: rate limit exhausted after iteration {iteration}"
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
                self._print_stats(iteration)
                return msg

            if action.type == ActionType.FAIL:
                msg = f"Task failed: {action.reason}"
                print(f"\n  {msg}")
                self._print_stats(iteration)
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

        msg = f"Reached maximum iterations ({self.max_iterations})"
        self._print_stats(self.max_iterations)
        return msg

    def _print_stats(self, iterations: int) -> None:
        """Print session statistics."""
        stats = self.client.stats
        print(f"\n  --- Session Stats ---")
        print(f"  Iterations: {iterations}")
        print(f"  API requests: {stats['total_requests']}")
        print(f"  Rate limits hit: {stats['rate_limits_hit']}")
        cost = self.client.get_model_cost()
        if cost == 0:
            print(f"  Premium requests consumed: 0 (model is FREE)")
        else:
            print(f"  Estimated premium requests: ~{int(iterations * cost)}")

    def _build_prompt(self, task: str, iteration: int, unchanged_count: int = 0) -> str:
        """Build the prompt for the current iteration.

        Args:
            task: The task description.
            iteration: Current iteration number.
            unchanged_count: Number of consecutive identical screenshots.
        """
        if iteration == 1:
            return (
                f"Task: {task}\n\n"
                "This is the current state of the screen. "
                "What is the first action to take?"
            )

        base = (
            f"Task: {task}\n\n"
            "This is the updated screen after the previous action. "
            "What is the next action? If the task is complete, respond with 'done'."
        )

        if unchanged_count >= 3:
            base += (
                f"\n\n⚠️ WARNING: The screen has NOT changed for {unchanged_count} "
                "consecutive actions. Your previous action may not have worked. "
                "Try a DIFFERENT approach, or if the task cannot be completed, "
                "respond with 'fail'."
            )
        elif unchanged_count >= 1:
            base += (
                "\n\nNote: The screen appears unchanged from the last action. "
                "Verify your action had the intended effect."
            )

        return base
