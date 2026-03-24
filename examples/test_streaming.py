"""
Example: Use streaming API to get real-time AI responses.

Demonstrates the SSE streaming capability with a simple text chat.

Usage:
    python examples/test_streaming.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.copilot.auth import CopilotAuth
from src.copilot.client import CopilotClient


def main():
    print("=" * 60)
    print("  Copilot Streaming API Test")
    print("=" * 60)
    print()

    auth = CopilotAuth()
    if not auth.is_authenticated:
        print("Not authenticated. Run: python -m src.copilot.auth")
        sys.exit(1)

    client = CopilotClient(auth=auth)

    prompt = "Explain in 3 sentences how a computer mouse works."
    print(f"Prompt: {prompt}")
    print()
    print("Streaming response:")
    print("-" * 40)

    try:
        for token in client.chat_stream(
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Be concise."},
                {"role": "user", "content": prompt},
            ],
            model="gpt-4o",
        ):
            print(token, end="", flush=True)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
    finally:
        client.close()

    print()
    print("-" * 40)
    print(f"\nStats: {client.stats}")
    print("✅ Streaming works!")


if __name__ == "__main__":
    main()
