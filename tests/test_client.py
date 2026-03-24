"""Tests for CopilotClient retry logic."""

from __future__ import annotations

import pytest

from src.copilot.client import CopilotClient, RateLimitError


class TestRateLimitError:
    """Test RateLimitError exception."""

    def test_basic_error(self):
        err = RateLimitError("test error")
        assert str(err) == "test error"
        assert err.retry_after is None

    def test_error_with_retry_after(self):
        err = RateLimitError("test", retry_after=30)
        assert err.retry_after == 30

    def test_is_exception(self):
        assert issubclass(RateLimitError, Exception)


class TestCopilotClientInit:
    """Test CopilotClient initialization (no network calls)."""

    def test_default_retries(self):
        # Can't make actual API calls, but can test init
        client = CopilotClient.__new__(CopilotClient)
        client.max_retries = 3
        client.base_retry_delay = 5.0
        assert client.max_retries == 3
        assert client.base_retry_delay == 5.0

    def test_model_cost_lookup(self):
        client = CopilotClient.__new__(CopilotClient)
        from src.copilot.config import CopilotConfig
        client.config = CopilotConfig()

        assert client.get_model_cost("gpt-4o") == 0
        assert client.get_model_cost("gpt-4.1") == 0
        assert client.get_model_cost("claude-sonnet-4") == 1
        assert client.get_model_cost("claude-opus-4.6") == 3
        assert client.get_model_cost("unknown-model") == 1.0  # default

    def test_stats_property(self):
        client = CopilotClient.__new__(CopilotClient)
        client._request_count = 10
        client._rate_limit_count = 2
        stats = client.stats
        assert stats["total_requests"] == 10
        assert stats["rate_limits_hit"] == 2
