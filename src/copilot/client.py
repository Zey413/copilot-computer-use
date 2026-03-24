"""
Copilot API client for chat completions.

Supports both text-only and vision (base64 image) requests.
Based on reverse engineering from github.com/nocoo/raven.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx

from .auth import CopilotAuth
from .config import CopilotConfig


class CopilotClient:
    """Client for GitHub Copilot's chat/completions API."""

    def __init__(
        self,
        auth: CopilotAuth | None = None,
        config: CopilotConfig | None = None,
    ):
        self.config = config or CopilotConfig()
        self.auth = auth or CopilotAuth(self.config)
        self._http = httpx.Client(timeout=60.0)

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Send a text-only chat completion request.

        Args:
            messages: OpenAI-format messages list.
            model: Model name (defaults to config.text_model).
            temperature: Sampling temperature.
            max_tokens: Maximum response tokens.

        Returns:
            Assistant's response text.
        """
        token = self.auth.get_copilot_token()
        headers = self.config.get_headers(token, vision=False)
        model = model or self.config.text_model

        resp = self._http.post(
            f"{self.config.api_base}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        return data["choices"][0]["message"]["content"]

    def vision(
        self,
        prompt: str,
        image_bytes: bytes,
        *,
        media_type: str = "image/png",
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Send a vision request with a base64-encoded image.

        Args:
            prompt: Text prompt describing what to analyze.
            image_bytes: Raw image bytes (PNG recommended).
            media_type: MIME type of the image.
            model: Vision model name (defaults to config.vision_model).
            temperature: Sampling temperature.
            max_tokens: Maximum response tokens.

        Returns:
            Assistant's response text describing the image.
        """
        token = self.auth.get_copilot_token()
        headers = self.config.get_headers(token, vision=True)
        model = model or self.config.vision_model

        b64_data = base64.b64encode(image_bytes).decode("ascii")

        resp = self._http.post(
            f"{self.config.api_base}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{b64_data}",
                                "detail": "auto",
                            },
                        },
                    ],
                }],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        return data["choices"][0]["message"]["content"]

    def vision_with_history(
        self,
        messages: list[dict[str, Any]],
        image_bytes: bytes,
        prompt: str,
        *,
        media_type: str = "image/png",
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Send a vision request with conversation history.

        Args:
            messages: Previous conversation messages.
            image_bytes: Raw image bytes for the latest screenshot.
            prompt: Text prompt for the current turn.
            media_type: MIME type of the image.
            model: Vision model name.
            temperature: Sampling temperature.
            max_tokens: Maximum response tokens.

        Returns:
            Assistant's response text.
        """
        token = self.auth.get_copilot_token()
        headers = self.config.get_headers(token, vision=True)
        model = model or self.config.vision_model

        b64_data = base64.b64encode(image_bytes).decode("ascii")

        # Append the new user message with image
        all_messages = list(messages) + [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{b64_data}",
                        "detail": "auto",
                    },
                },
            ],
        }]

        resp = self._http.post(
            f"{self.config.api_base}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": all_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        return data["choices"][0]["message"]["content"]

    def close(self) -> None:
        """Close the HTTP client."""
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
