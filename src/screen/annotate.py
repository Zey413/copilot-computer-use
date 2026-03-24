"""
Screenshot annotation module.

Adds visual aids to screenshots to help the AI model identify
clickable elements and their coordinates more accurately.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont


@dataclass
class GridConfig:
    """Configuration for grid overlay."""

    spacing: int = 100  # Pixels between grid lines
    color: tuple[int, int, int, int] = (255, 0, 0, 80)  # Semi-transparent red
    label_color: tuple[int, int, int] = (255, 0, 0)
    font_size: int = 12
    show_labels: bool = True  # Show coordinate labels at intersections


@dataclass
class CrosshairConfig:
    """Configuration for crosshair markers."""

    size: int = 20  # Crosshair arm length
    color: tuple[int, int, int] = (0, 255, 0)  # Green
    width: int = 2


class ScreenAnnotator:
    """Annotate screenshots with visual aids for better AI understanding."""

    def __init__(self, grid_config: GridConfig | None = None):
        self.grid = grid_config or GridConfig()

    def add_grid(self, image: Image.Image) -> Image.Image:
        """Add a coordinate grid overlay to the screenshot.

        This helps the AI model estimate coordinates more accurately
        by providing visible reference points.

        Args:
            image: PIL Image to annotate.

        Returns:
            New annotated PIL Image (original is not modified).
        """
        img = image.copy().convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        w, h = img.size
        spacing = self.grid.spacing

        # Try to load a small font, fall back to default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", self.grid.font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", self.grid.font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()

        # Draw vertical lines
        for x in range(0, w, spacing):
            draw.line([(x, 0), (x, h)], fill=self.grid.color, width=1)
            if self.grid.show_labels and x > 0:
                draw.text((x + 2, 2), str(x), fill=self.grid.label_color, font=font)

        # Draw horizontal lines
        for y in range(0, h, spacing):
            draw.line([(0, y), (w, y)], fill=self.grid.color, width=1)
            if self.grid.show_labels and y > 0:
                draw.text((2, y + 2), str(y), fill=self.grid.label_color, font=font)

        # Composite overlay onto image
        result = Image.alpha_composite(img, overlay)
        return result.convert("RGB")

    def add_crosshair(
        self,
        image: Image.Image,
        x: int,
        y: int,
        config: CrosshairConfig | None = None,
    ) -> Image.Image:
        """Add a crosshair marker at a specific position.

        Useful for marking the last click position or highlighting a target.

        Args:
            image: PIL Image to annotate.
            x: X coordinate for crosshair center.
            y: Y coordinate for crosshair center.
            config: Crosshair style configuration.

        Returns:
            New annotated PIL Image.
        """
        cfg = config or CrosshairConfig()
        img = image.copy()
        draw = ImageDraw.Draw(img)

        # Horizontal line
        draw.line(
            [(x - cfg.size, y), (x + cfg.size, y)],
            fill=cfg.color,
            width=cfg.width,
        )
        # Vertical line
        draw.line(
            [(x, y - cfg.size), (x, y + cfg.size)],
            fill=cfg.color,
            width=cfg.width,
        )
        # Center dot
        r = cfg.width + 1
        draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=cfg.color)

        return img

    def add_numbered_regions(
        self,
        image: Image.Image,
        regions: list[tuple[int, int, int, int]],
        color: tuple[int, int, int] = (0, 120, 255),
    ) -> Image.Image:
        """Draw numbered bounding boxes around detected UI regions.

        Args:
            image: PIL Image to annotate.
            regions: List of (x1, y1, x2, y2) bounding boxes.
            color: Box and label color.

        Returns:
            New annotated PIL Image.
        """
        img = image.copy()
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
            except (OSError, IOError):
                font = ImageFont.load_default()

        for i, (x1, y1, x2, y2) in enumerate(regions, 1):
            # Draw bounding box
            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=2)

            # Draw number label with background
            label = str(i)
            bbox = font.getbbox(label)
            lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
            label_bg = [(x1, y1 - lh - 4), (x1 + lw + 6, y1)]
            draw.rectangle(label_bg, fill=color)
            draw.text((x1 + 3, y1 - lh - 2), label, fill=(255, 255, 255), font=font)

        return img

    @staticmethod
    def to_bytes(image: Image.Image, format: str = "PNG") -> bytes:
        """Convert annotated image to bytes.

        Args:
            image: PIL Image.
            format: Output format (PNG recommended for Copilot API).

        Returns:
            Image bytes.
        """
        buf = io.BytesIO()
        image.save(buf, format=format)
        return buf.getvalue()
