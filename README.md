# copilot-computer-use

**English** | [中文](README_zh.md)

> **The world's first free Computer Use agent powered by GitHub Copilot API.**

Screenshot → Vision Analysis → Action Execution — all through your Copilot subscription ($10/mo or free for students).

## Why?

Every Computer Use agent today requires expensive Vision API calls ($$$). We discovered that **GitHub Copilot API supports base64 image input** via the `copilot-vision-request: true` header. This means you can build a fully functional Computer Use agent at **zero additional cost** beyond your existing Copilot subscription.

## How It Works

```
┌─────────────────────────────────────────────────┐
│              Agent Control Loop                  │
│                                                  │
│  1. 📸 Capture screenshot (mss + Pillow)         │
│  2. 🔄 Encode to base64 PNG                      │
│  3. 👁️ Analyze via Copilot Vision API            │
│     (copilot-vision-request: true header)        │
│  4. 🧠 Plan next action via Copilot Text API     │
│  5. ⚡ Execute action (pyautogui)                │
│  6. 🔁 Repeat until task complete                │
└─────────────────────────────────────────────────┘
         ↕ All API calls go through ↕
┌─────────────────────────────────────────────────┐
│        Copilot API Adapter                       │
│  • GitHub OAuth Device Flow authentication       │
│  • Automatic JWT token refresh                   │
│  • VS Code version spoofing                      │
│  • copilot-vision-request header management      │
└─────────────────────────────────────────────────┘
```

## Key Innovation

| Aspect | Traditional Agent | copilot-computer-use |
|--------|-------------------|---------------------|
| Vision API Cost | $0.01-0.05/screenshot | **$0 (included in Copilot)** |
| Text Reasoning Cost | $0.003-0.06/request | **$0 (included in Copilot)** |
| Monthly Cost | $20-100+ | **$10/mo (Copilot) or free** |
| Models Available | 1 provider | GPT-4o, Claude, Gemini |

## Prerequisites

- Python 3.11+
- GitHub account with Copilot subscription (Individual, Business, or Enterprise)
- macOS or Linux (Windows support planned)

## Quick Start

```bash
# Clone
git clone https://github.com/Zey413/copilot-computer-use.git
cd copilot-computer-use

# Install
pip install -e .

# Authenticate with GitHub (one-time)
python -m src.copilot.auth

# Run
python -m src.main "Open Chrome and search for the weather"
```

## Architecture

```
src/
├── main.py                 # Entry point + CLI
├── copilot/
│   ├── auth.py             # GitHub OAuth Device Flow + JWT refresh
│   ├── client.py           # Copilot chat/completions API client
│   └── config.py           # API endpoints, headers, version spoofing
├── agent/
│   ├── loop.py             # Core agent control loop
│   ├── planner.py          # Task planning via text reasoning
│   └── actions.py          # Action definitions (click, type, scroll...)
├── screen/
│   ├── capture.py          # Screenshot capture (mss + Pillow)
│   └── annotate.py         # Optional: annotate screenshots with markers
└── executor/
    ├── base.py             # Abstract executor interface
    ├── macos.py            # macOS executor (pyautogui + AppleScript)
    └── linux.py            # Linux executor (pyautogui + xdotool)
```

## How Copilot Vision Works

The key discovery: Copilot's `chat/completions` API accepts base64-encoded images when you include the `copilot-vision-request: true` header:

```python
import httpx

response = httpx.post(
    "https://api.githubcopilot.com/chat/completions",
    headers={
        "Authorization": f"Bearer {copilot_jwt}",
        "copilot-vision-request": "true",
        "editor-version": "vscode/1.104.3",
        # ... other headers
    },
    json={
        "model": "gpt-4o",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "What do you see on this screen?"},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{screenshot_b64}"
                }}
            ]
        }]
    }
)
```

## Research Background

This project is based on extensive research documented in Reviews #001-#013:
- **Raven** ([nocoo/raven](https://github.com/nocoo/raven)): Proved Copilot API can be proxied with full Anthropic↔OpenAI translation
- **Copilot Vision**: Confirmed base64 support via 6+ open-source projects (LiteLLM, OpenCode, LobeHub, etc.)
- **Market Gap**: Zero existing projects combine Copilot proxy + Computer Use

## Supported Models (via Copilot)

- GPT-4o / GPT-4.1 (Vision ✅)
- Claude Sonnet 4 / Opus 4 (Vision ✅)
- Gemini 2.5 Pro / 3 Flash (Vision ✅)
- o4-mini (Reasoning)
- And more as GitHub adds them

## Limitations

- **Experimental**: This is a research project, not production software
- **Rate Limits**: Copilot has rate limits; aggressive screenshot loops may be throttled
- **ToS Gray Area**: Using Copilot API beyond IDE integration may not be explicitly permitted
- **Image Formats**: PNG is most reliable; JPEG works; WebP may have issues
- **macOS/Linux only**: Windows executor not yet implemented

## Acknowledgments

- [Raven](https://github.com/nocoo/raven) — Inspiration for Copilot API authentication and format translation
- [self-operating-computer](https://github.com/OthersideAI/self-operating-computer) — Reference for lightweight Computer Use architecture
- [copilot-api](https://github.com/ericc-ch/copilot-api) — Early Copilot reverse engineering work

## License

MIT
