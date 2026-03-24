"""
GitHub Copilot API configuration.

Contains all endpoints, headers, and version spoofing logic.
Based on reverse engineering from github.com/nocoo/raven.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class CopilotConfig:
    """Configuration for Copilot API requests."""

    # API endpoints
    api_base: str = "https://api.githubcopilot.com"
    github_client_id: str = "Iv1.b507a08c87ecfe98"  # VS Code's OAuth App
    device_code_url: str = "https://github.com/login/device/code"
    access_token_url: str = "https://github.com/login/oauth/access_token"
    copilot_token_url: str = "https://api.github.com/copilot_internal/v2/token"

    # Version spoofing
    vscode_version: str = "1.104.3"
    copilot_chat_version: str = "0.26.7"

    # Models
    vision_model: str = "gpt-4o"
    text_model: str = "gpt-4o"

    # Token path
    token_path: str = "~/.copilot-computer-use/tokens"

    def get_headers(self, token: str, *, vision: bool = False) -> dict[str, str]:
        """Build request headers that mimic VS Code Copilot Chat.

        Args:
            token: Copilot JWT bearer token.
            vision: If True, include copilot-vision-request header.

        Returns:
            Dict of headers for the Copilot API request.
        """
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "editor-version": f"vscode/{self.vscode_version}",
            "editor-plugin-version": f"copilot-chat/{self.copilot_chat_version}",
            "user-agent": f"GitHubCopilotChat/{self.copilot_chat_version}",
            "copilot-integration-id": "vscode-chat",
            "x-vscode-user-agent-library-version": "electron-fetch",
            "openai-intent": "conversation-panel",
            "x-github-api-version": "2025-04-01",
            "x-request-id": str(uuid.uuid4()),
        }
        if vision:
            headers["copilot-vision-request"] = "true"
        return headers

    def get_github_headers(self, github_token: str) -> dict[str, str]:
        """Build headers for GitHub API requests (token refresh etc.)."""
        return {
            "Authorization": f"token {github_token}",
            "Accept": "application/json",
            "editor-version": f"vscode/{self.vscode_version}",
            "editor-plugin-version": f"copilot-chat/{self.copilot_chat_version}",
            "user-agent": f"GitHubCopilotChat/{self.copilot_chat_version}",
        }
