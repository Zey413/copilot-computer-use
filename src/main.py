"""
copilot-computer-use: Free Computer Use agent powered by GitHub Copilot API.

Usage:
    python -m src.main "Open Chrome and search for the weather"
    python -m src.main --model gpt-4o "Click on the Finder icon"
"""

from __future__ import annotations

import argparse
import platform
import sys

from .agent.loop import AgentLoop
from .copilot.auth import CopilotAuth
from .copilot.client import CopilotClient
from .copilot.config import CopilotConfig
from .screen.capture import ScreenCapture


def get_executor():
    """Get the appropriate executor for the current platform."""
    system = platform.system()
    if system == "Darwin":
        from .executor.macos import MacOSExecutor
        return MacOSExecutor()
    elif system == "Linux":
        # Linux executor (TODO: implement)
        from .executor.macos import MacOSExecutor  # Fallback to pyautogui
        print("Warning: Using macOS executor on Linux (pyautogui should still work)")
        return MacOSExecutor()
    else:
        print(f"Unsupported platform: {system}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Free Computer Use agent powered by GitHub Copilot API",
    )
    parser.add_argument(
        "task",
        help="Natural language description of the task to perform",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="Copilot model to use (default: gpt-4o)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=50,
        help="Maximum agent loop iterations (default: 50)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between iterations in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=1280,
        help="Max screenshot width in pixels (default: 1280)",
    )
    parser.add_argument(
        "--max-height",
        type=int,
        default=800,
        help="Max screenshot height in pixels (default: 800)",
    )

    args = parser.parse_args()

    # Setup
    config = CopilotConfig(
        vision_model=args.model,
        text_model=args.model,
    )
    auth = CopilotAuth(config)

    if not auth.is_authenticated:
        print("Not authenticated. Starting GitHub Device Flow...")
        auth.device_flow_login()

    client = CopilotClient(auth=auth, config=config)
    executor = get_executor()
    screen = ScreenCapture(max_width=args.max_width, max_height=args.max_height)

    agent = AgentLoop(
        client=client,
        executor=executor,
        screen=screen,
        max_iterations=args.max_iterations,
        loop_delay=args.delay,
    )

    # Run
    try:
        result = agent.run(args.task)
        print(f"\nResult: {result}")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
