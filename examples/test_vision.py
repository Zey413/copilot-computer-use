"""
Example: Test Copilot Vision API connection.

This script verifies your Copilot auth is working and that Vision
(base64 image) requests are accepted. It creates a simple test image
and sends it to the API.

Usage:
    python examples/test_vision.py
"""

from __future__ import annotations

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.copilot.auth import CopilotAuth
from src.copilot.client import CopilotClient, MODEL_MULTIPLIERS
from src.copilot.config import CopilotConfig


def create_test_image() -> bytes:
    """Create a simple test PNG image with text."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow not installed. Run: pip install Pillow")
        sys.exit(1)

    img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw some shapes and text
    draw.rectangle([(20, 20), (180, 80)], fill=(66, 135, 245), outline=(0, 0, 0))
    draw.rectangle([(220, 20), (380, 80)], fill=(245, 66, 66), outline=(0, 0, 0))
    draw.ellipse([(120, 100), (280, 180)], fill=(66, 245, 135), outline=(0, 0, 0))

    # Try to add text
    try:
        draw.text((60, 40), "BLUE", fill=(255, 255, 255))
        draw.text((270, 40), "RED", fill=(255, 255, 255))
        draw.text((170, 130), "GREEN", fill=(0, 0, 0))
    except Exception:
        pass  # Skip text if font issues

    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def main():
    print("=" * 60)
    print("  Copilot Vision API Test")
    print("=" * 60)
    print()

    # Step 1: Check auth
    print("1. Checking authentication...")
    auth = CopilotAuth()
    if not auth.is_authenticated:
        print("   Not authenticated. Run: python -m src.copilot.auth")
        sys.exit(1)
    print("   ✅ GitHub token found")

    # Step 2: Get Copilot JWT
    print("2. Getting Copilot JWT...")
    try:
        token = auth.get_copilot_token()
        print(f"   ✅ JWT obtained (prefix: {token[:15]}...)")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        sys.exit(1)

    # Step 3: Show model costs
    print("3. Model costs:")
    for model, cost in sorted(MODEL_MULTIPLIERS.items(), key=lambda x: x[1]):
        label = "FREE" if cost == 0 else f"{cost}x"
        print(f"   {model:25s} → {label}")

    # Step 4: Create test image
    print("4. Creating test image...")
    image_bytes = create_test_image()
    print(f"   ✅ Test image: {len(image_bytes)} bytes (400x200 PNG)")

    # Step 5: Send Vision request
    print("5. Sending Vision request to Copilot API (gpt-4o)...")
    print("   Headers: copilot-vision-request: true")
    print()

    client = CopilotClient(auth=auth)
    try:
        response = client.vision(
            prompt="Describe what you see in this image. List the shapes and their colors.",
            image_bytes=image_bytes,
            model="gpt-4o",
        )
        print("   ✅ Vision API response:")
        print("   " + "-" * 50)
        for line in response.split("\n"):
            print(f"   {line}")
        print("   " + "-" * 50)
    except Exception as e:
        print(f"   ❌ Vision request failed: {e}")
        print()
        print("   Possible causes:")
        print("   - Copilot subscription may not support vision")
        print("   - Rate limit reached")
        print("   - Network issue")
        sys.exit(1)
    finally:
        client.close()

    # Step 6: Show stats
    print()
    print(f"6. Stats: {client.stats}")
    print()
    print("✅ All tests passed! Your Copilot Vision setup is working.")
    print("   Run: python -m src.main \"Your task here\"")


if __name__ == "__main__":
    main()
