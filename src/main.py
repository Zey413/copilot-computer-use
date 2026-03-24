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


def get_executor(prefer_xdotool: bool = False):
    """Get the appropriate executor for the current platform.

    Args:
        prefer_xdotool: On Linux, prefer xdotool for better Unicode typing support.
    """
    system = platform.system()
    if system == "Darwin":
        from .executor.macos import MacOSExecutor

        return MacOSExecutor()
    elif system == "Linux":
        from .executor.linux import LinuxExecutor

        return LinuxExecutor(prefer_xdotool=prefer_xdotool)
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
    parser.add_argument(
        "--grid",
        action="store_true",
        help="Overlay coordinate grid on screenshots (helps AI with positioning)",
    )
    parser.add_argument(
        "--grid-spacing",
        type=int,
        default=100,
        help="Grid line spacing in pixels (default: 100)",
    )
    parser.add_argument(
        "--xdotool",
        action="store_true",
        help="Linux only: prefer xdotool for typing (better Unicode support)",
    )
    parser.add_argument(
        "--save-screenshots",
        type=str,
        default=None,
        metavar="DIR",
        help="Save each iteration's screenshot to DIR for debugging",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Use streaming API for faster perceived response time",
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
    executor = get_executor(prefer_xdotool=args.xdotool)
    screen = ScreenCapture(max_width=args.max_width, max_height=args.max_height)

    # Optional: grid annotation
    annotator = None
    if args.grid:
        from .screen.annotate import GridConfig, ScreenAnnotator

        annotator = ScreenAnnotator(GridConfig(spacing=args.grid_spacing))

    agent = AgentLoop(
        client=client,
        executor=executor,
        screen=screen,
        annotator=annotator,
        max_iterations=args.max_iterations,
        loop_delay=args.delay,
        save_screenshots=args.save_screenshots,
        use_streaming=args.stream,
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
