"""
Screenshot capture module.

Uses mss for fast cross-platform screenshot capture,
and Pillow for image processing / resizing.
"""

from __future__ import annotations

import base64
import io

from PIL import Image

try:
    import mss
except ImportError:
    mss = None


class ScreenCapture:
    """Captures screenshots and encodes them for the Copilot Vision API."""

    def __init__(self, max_width: int = 1280, max_height: int = 800):
        """Initialize screen capture.

        Args:
            max_width: Maximum screenshot width (pixels). Images wider are scaled down.
            max_height: Maximum screenshot height (pixels). Images taller are scaled down.
        """
        self.max_width = max_width
        self.max_height = max_height

    def capture(self) -> bytes:
        """Capture the primary monitor and return PNG bytes.

        Returns:
            PNG-encoded screenshot bytes, resized if needed.

        Raises:
            RuntimeError: If mss is not installed.
        """
        if mss is None:
            raise RuntimeError("mss is required for screenshots: pip install mss")

        with mss.mss() as sct:
            # Capture primary monitor
            monitor = sct.monitors[1]  # [0] is "all monitors combined"
            raw = sct.grab(monitor)

            # Convert to PIL Image
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

        # Resize if needed (maintain aspect ratio)
        img = self._resize(img)

        # Encode to PNG bytes
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    def capture_base64(self) -> str:
        """Capture screenshot and return as base64 string.

        Returns:
            Base64-encoded PNG string.
        """
        png_bytes = self.capture()
        return base64.b64encode(png_bytes).decode("ascii")

    def _resize(self, img: Image.Image) -> Image.Image:
        """Resize image to fit within max dimensions, maintaining aspect ratio.

        Args:
            img: PIL Image to resize.

        Returns:
            Resized PIL Image (or original if already within bounds).
        """
        w, h = img.size
        if w <= self.max_width and h <= self.max_height:
            return img

        # Calculate scale factor
        scale = min(self.max_width / w, self.max_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        return img.resize((new_w, new_h), Image.LANCZOS)
