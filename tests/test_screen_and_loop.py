"""Tests for screen capture and annotation modules."""

from __future__ import annotations

import io

import pytest

from src.screen.capture import ScreenCapture


class TestScreenCaptureResize:
    """Test ScreenCapture._resize() logic (no actual screenshots needed)."""

    def test_no_resize_when_within_bounds(self):
        """Image smaller than max should not be resized."""
        from PIL import Image

        sc = ScreenCapture(max_width=1280, max_height=800)
        img = Image.new("RGB", (640, 480))
        result = sc._resize(img)
        assert result.size == (640, 480)

    def test_resize_wide_image(self):
        """Wide image should be scaled to fit max_width."""
        from PIL import Image

        sc = ScreenCapture(max_width=1280, max_height=800)
        img = Image.new("RGB", (2560, 800))
        result = sc._resize(img)
        assert result.size[0] == 1280
        assert result.size[1] == 400  # Proportional

    def test_resize_tall_image(self):
        """Tall image should be scaled to fit max_height."""
        from PIL import Image

        sc = ScreenCapture(max_width=1280, max_height=800)
        img = Image.new("RGB", (1280, 1600))
        result = sc._resize(img)
        assert result.size[0] == 640
        assert result.size[1] == 800

    def test_resize_both_dimensions(self):
        """Image exceeding both dimensions uses minimum scale factor."""
        from PIL import Image

        sc = ScreenCapture(max_width=100, max_height=100)
        img = Image.new("RGB", (400, 200))
        result = sc._resize(img)
        # Scale factor = min(100/400, 100/200) = 0.25
        assert result.size == (100, 50)

    def test_exact_boundary_no_resize(self):
        """Image exactly at max dimensions should not be resized."""
        from PIL import Image

        sc = ScreenCapture(max_width=1280, max_height=800)
        img = Image.new("RGB", (1280, 800))
        result = sc._resize(img)
        assert result.size == (1280, 800)


class TestScreenAnnotator:
    """Test annotation functionality."""

    def test_grid_overlay_returns_image(self):
        """Grid overlay should return a valid image."""
        from PIL import Image

        from src.screen.annotate import GridConfig, ScreenAnnotator

        annotator = ScreenAnnotator(GridConfig(spacing=50))
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        result = annotator.add_grid(img)

        assert isinstance(result, Image.Image)
        assert result.size == (200, 200)
        assert result.mode == "RGB"

    def test_grid_does_not_modify_original(self):
        """Grid overlay should not modify the original image."""
        from PIL import Image

        from src.screen.annotate import ScreenAnnotator

        annotator = ScreenAnnotator()
        original = Image.new("RGB", (200, 200), color=(255, 255, 255))
        original_copy = original.copy()
        annotator.add_grid(original)

        # Compare pixels
        assert list(original.getdata()) == list(original_copy.getdata())

    def test_crosshair_at_center(self):
        """Crosshair should be drawn at specified coordinates."""
        from PIL import Image

        from src.screen.annotate import ScreenAnnotator

        annotator = ScreenAnnotator()
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        result = annotator.add_crosshair(img, 100, 100)

        assert isinstance(result, Image.Image)
        # Check that the center pixel is not white (crosshair drawn)
        pixel = result.getpixel((100, 100))
        assert pixel != (255, 255, 255)

    def test_numbered_regions(self):
        """Numbered regions should draw boxes."""
        from PIL import Image

        from src.screen.annotate import ScreenAnnotator

        annotator = ScreenAnnotator()
        img = Image.new("RGB", (400, 400), color=(255, 255, 255))
        regions = [(10, 10, 100, 50), (150, 150, 300, 200)]
        result = annotator.add_numbered_regions(img, regions)

        assert isinstance(result, Image.Image)
        assert result.size == (400, 400)

    def test_to_bytes_png(self):
        """to_bytes should return valid PNG bytes."""
        from PIL import Image

        from src.screen.annotate import ScreenAnnotator

        img = Image.new("RGB", (100, 100))
        data = ScreenAnnotator.to_bytes(img, format="PNG")

        assert isinstance(data, bytes)
        assert data[:4] == b"\x89PNG"  # PNG magic bytes
        assert len(data) > 0


class TestAgentPromptBuilding:
    """Test prompt construction logic."""

    def test_first_iteration_prompt(self):
        """First iteration should include 'first action' phrasing."""
        from unittest.mock import MagicMock

        from src.agent.loop import AgentLoop

        loop = AgentLoop.__new__(AgentLoop)
        loop.annotator = None
        prompt = loop._build_prompt("test task", iteration=1, unchanged_count=0)

        assert "test task" in prompt
        assert "first action" in prompt

    def test_normal_iteration_prompt(self):
        """Subsequent iterations should ask for next action."""
        from src.agent.loop import AgentLoop

        loop = AgentLoop.__new__(AgentLoop)
        loop.annotator = None
        prompt = loop._build_prompt("test task", iteration=5, unchanged_count=0)

        assert "test task" in prompt
        assert "next action" in prompt

    def test_unchanged_screen_warning(self):
        """Prompt should warn when screen hasn't changed."""
        from src.agent.loop import AgentLoop

        loop = AgentLoop.__new__(AgentLoop)
        loop.annotator = None
        prompt = loop._build_prompt("test task", iteration=5, unchanged_count=1)

        assert "unchanged" in prompt.lower()

    def test_stuck_screen_strong_warning(self):
        """Prompt should strongly warn after 3+ unchanged screenshots."""
        from src.agent.loop import AgentLoop

        loop = AgentLoop.__new__(AgentLoop)
        loop.annotator = None
        prompt = loop._build_prompt("test task", iteration=5, unchanged_count=4)

        assert "WARNING" in prompt
        assert "DIFFERENT" in prompt
        assert "4" in prompt  # Should mention the count
