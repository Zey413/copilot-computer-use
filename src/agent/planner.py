"""Task planning module for the agent."""

from __future__ import annotations

from ..copilot.client import CopilotClient


class TaskPlanner:
    """Plans multi-step tasks using text reasoning (no vision needed).

    Useful for breaking complex tasks into steps before starting the
    vision-based agent loop.
    """

    def __init__(self, client: CopilotClient):
        self.client = client

    def plan(self, task: str) -> list[str]:
        """Break a complex task into simple steps.

        Args:
            task: Natural language task description.

        Returns:
            List of step descriptions.
        """
        response = self.client.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a task planner for a Computer Use agent that controls "
                        "a desktop computer. Break the given task into simple, atomic steps "
                        "that can each be accomplished with basic mouse/keyboard actions.\n\n"
                        "Respond with a numbered list, one step per line.\n"
                        "Example:\n"
                        "1. Click on the Chrome icon in the dock\n"
                        "2. Click on the address bar\n"
                        "3. Type 'weather today'\n"
                        "4. Press Enter to search"
                    ),
                },
                {"role": "user", "content": f"Task: {task}"},
            ],
        )

        # Parse numbered list
        steps = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and line[0].isdigit():
                # Remove number prefix
                idx = line.find(".")
                if idx != -1:
                    step = line[idx + 1:].strip()
                    if step:
                        steps.append(step)

        return steps if steps else [task]  # Fallback to original task
