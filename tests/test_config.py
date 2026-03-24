"""Tests for Copilot API configuration and headers."""

from __future__ import annotations

from src.copilot.config import CopilotConfig


class TestCopilotConfig:
    """Test CopilotConfig header generation."""

    def test_default_values(self):
        config = CopilotConfig()
        assert config.api_base == "https://api.githubcopilot.com"
        assert config.github_client_id == "Iv1.b507a08c87ecfe98"
        assert config.vision_model == "gpt-4o"
        assert config.text_model == "gpt-4o"

    def test_get_headers_basic(self):
        config = CopilotConfig()
        headers = config.get_headers("test-token", vision=False)

        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"
        assert "vscode" in headers["editor-version"]
        assert "copilot-chat" in headers["editor-plugin-version"]
        assert headers["copilot-integration-id"] == "vscode-chat"
        assert headers["x-github-api-version"] == "2025-04-01"
        assert "x-request-id" in headers  # UUID should be present
        assert "copilot-vision-request" not in headers

    def test_get_headers_with_vision(self):
        config = CopilotConfig()
        headers = config.get_headers("test-token", vision=True)

        assert headers["copilot-vision-request"] == "true"
        assert headers["Authorization"] == "Bearer test-token"

    def test_get_headers_without_vision(self):
        config = CopilotConfig()
        headers = config.get_headers("test-token", vision=False)

        assert "copilot-vision-request" not in headers

    def test_version_spoofing(self):
        config = CopilotConfig(vscode_version="2.0.0", copilot_chat_version="1.0.0")
        headers = config.get_headers("token", vision=False)

        assert headers["editor-version"] == "vscode/2.0.0"
        assert headers["editor-plugin-version"] == "copilot-chat/1.0.0"
        assert headers["user-agent"] == "GitHubCopilotChat/1.0.0"

    def test_unique_request_ids(self):
        config = CopilotConfig()
        h1 = config.get_headers("token", vision=False)
        h2 = config.get_headers("token", vision=False)

        assert h1["x-request-id"] != h2["x-request-id"]

    def test_github_headers(self):
        config = CopilotConfig()
        headers = config.get_github_headers("gh-token-123")

        assert headers["Authorization"] == "token gh-token-123"
        assert headers["Accept"] == "application/json"
        assert "vscode" in headers["editor-version"]


class TestModelMultipliers:
    """Test model cost awareness."""

    def test_import_multipliers(self):
        from src.copilot.client import MODEL_MULTIPLIERS

        assert MODEL_MULTIPLIERS["gpt-4o"] == 0
        assert MODEL_MULTIPLIERS["gpt-4.1"] == 0
        assert MODEL_MULTIPLIERS["claude-sonnet-4"] == 1
        assert MODEL_MULTIPLIERS["claude-opus-4.6"] == 3

    def test_free_models(self):
        from src.copilot.client import MODEL_MULTIPLIERS

        free_models = [k for k, v in MODEL_MULTIPLIERS.items() if v == 0]
        assert "gpt-4o" in free_models
        assert "gpt-4.1" in free_models
