"""
Copilot API client for chat completions.

Supports both text-only and vision (base64 image) requests.
Includes automatic retry with exponential backoff for rate limits.
Based on reverse engineering from github.com/nocoo/raven.
"""

from __future__ import annotations

import base64
import time
from typing import Any

import httpx

from .auth import CopilotAuth
from .config import CopilotConfig

# Premium request multipliers (0 = free, no quota consumed)
MODEL_MULTIPLIERS = {
    "gpt-4o": 0,
    "gpt-4.1": 0,
    "gpt-5-mini": 0,
    "raptor-mini": 0,
    "grok-code-fast-1": 0.25,
    "claude-haiku-4.5": 0.33,
    "gemini-3-flash": 0.33,
    "claude-sonnet-4": 1,
    "claude-sonnet-4.5": 1,
    "claude-sonnet-4.6": 1,
    "gemini-2.5-pro": 1,
    "gemini-3-pro": 1,
    "claude-opus-4.5": 3,
    "claude-opus-4.6": 3,
}


class RateLimitError(Exception):
    """Raised when all retries are exhausted after 429 responses."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class CopilotClient:
    """Client for GitHub Copilot's chat/completions API.

    Features:
    - Automatic retry with exponential backoff on 429 rate limit
    - Vision support via base64 images + copilot-vision-request header
    - Model cost awareness (warns about premium request consumption)
    """

    def __init__(
        self,
        auth: CopilotAuth | None = None,
        config: CopilotConfig | None = None,
        max_retries: int = 3,
        base_retry_delay: float = 5.0,
    ):
        """Initialize the Copilot API client.

        Args:
            auth: Authentication handler.
            config: API configuration.
            max_retries: Maximum number of retries on 429 errors.
            base_retry_delay: Base delay in seconds for exponential backoff.
        """
        self.config = config or CopilotConfig()
        self.auth = auth or CopilotAuth(self.config)
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay
        self._http = httpx.Client(timeout=60.0)
        self._request_count = 0
        self._rate_limit_count = 0

    def _request_with_retry(
        self,
        payload: dict[str, Any],
        *,
        vision: bool = False,
    ) -> dict[str, Any]:
        """Send a request to Copilot API with automatic retry on 429.

        Args:
            payload: The JSON payload for chat/completions.
            vision: Whether this is a vision request.

        Returns:
            Parsed JSON response.

        Raises:
            RateLimitError: If all retries are exhausted.
            httpx.HTTPStatusError: For non-429 HTTP errors.
        """
        for attempt in range(self.max_retries + 1):
            token = self.auth.get_copilot_token()
            headers = self.config.get_headers(token, vision=vision)

            resp = self._http.post(
                f"{self.config.api_base}/chat/completions",
                headers=headers,
                json=payload,
            )

            self._request_count += 1

            if resp.status_code == 429:
                self._rate_limit_count += 1

                if attempt >= self.max_retries:
                    retry_after = resp.headers.get("Retry-After")
                    raise RateLimitError(
                        f"Rate limited after {self.max_retries + 1} attempts. "
                        f"Total requests: {self._request_count}, "
                        f"Rate limits hit: {self._rate_limit_count}",
                        retry_after=int(retry_after) if retry_after else None,
                    )

                # Exponential backoff: 5s, 10s, 20s, ...
                # Also respect Retry-After header if present
                retry_after_header = resp.headers.get("Retry-After")
                if retry_after_header and retry_after_header.isdigit():
                    delay = min(int(retry_after_header), 120)  # Cap at 2 minutes
                else:
                    delay = self.base_retry_delay * (2 ** attempt)

                print(f"  Rate limited (429). Retry {attempt + 1}/{self.max_retries} "
                      f"in {delay:.0f}s...")
                time.sleep(delay)
                continue

            resp.raise_for_status()
            return resp.json()

        # Should not reach here, but just in case
        raise RateLimitError("Unexpected retry loop exit")

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
        model = model or self.config.text_model

        data = self._request_with_retry(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            },
            vision=False,
        )

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
        model = model or self.config.vision_model
        b64_data = base64.b64encode(image_bytes).decode("ascii")

        data = self._request_with_retry(
            {
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
            vision=True,
        )

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

        data = self._request_with_retry(
            {
                "model": model,
                "messages": all_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            },
            vision=True,
        )

        return data["choices"][0]["message"]["content"]

    def get_model_cost(self, model: str | None = None) -> float:
        """Get the premium request multiplier for a model.

        Args:
            model: Model name. Defaults to vision_model.

        Returns:
            Multiplier (0 = free, 1 = standard, 3 = premium).
        """
        model = model or self.config.vision_model
        # Try exact match first, then prefix match
        if model in MODEL_MULTIPLIERS:
            return MODEL_MULTIPLIERS[model]
        for prefix, cost in MODEL_MULTIPLIERS.items():
            if model.startswith(prefix):
                return cost
        return 1.0  # Default: assume 1x

    @property
    def stats(self) -> dict[str, int]:
        """Get client usage statistics."""
        return {
            "total_requests": self._request_count,
            "rate_limits_hit": self._rate_limit_count,
        }

    def close(self) -> None:
        """Close the HTTP client."""
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
