# Contributing to copilot-computer-use

Thanks for your interest in contributing! This project is experimental and welcomes contributions of all kinds.

## Development Setup

```bash
# Clone
git clone https://github.com/Zey413/copilot-computer-use.git
cd copilot-computer-use

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
```

## Project Structure

```
src/
├── copilot/     # GitHub Copilot API integration
│   ├── auth.py      # OAuth Device Flow + JWT refresh
│   ├── client.py    # API client (text, vision, streaming)
│   └── config.py    # Headers, endpoints, version spoofing
├── agent/       # Agent control loop
│   ├── loop.py      # Core loop: screenshot → analyze → act
│   ├── actions.py   # Action types and JSON parsing
│   └── planner.py   # Task decomposition
├── screen/      # Screen capture
│   ├── capture.py   # mss + Pillow screenshot
│   └── annotate.py  # Grid overlay, crosshairs, numbered regions
├── executor/    # Desktop automation
│   ├── base.py      # Abstract executor interface
│   ├── macos.py     # macOS (pyautogui)
│   └── linux.py     # Linux (pyautogui + xdotool)
└── main.py      # CLI entry point
```

## How to Contribute

### Bug Reports
- Open an issue with steps to reproduce
- Include your OS, Python version, and Copilot plan

### Feature Requests
- Open an issue describing the feature
- Explain the use case and expected behavior

### Code Contributions

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Write tests for your changes
4. Ensure all tests pass: `pytest tests/ -v`
5. Ensure lint passes: `ruff check src/ tests/`
6. Commit with a descriptive message
7. Open a Pull Request

### Areas Where Help Is Needed

- **Windows executor** — We need `src/executor/windows.py` using pyautogui
- **Multi-monitor support** — Select which monitor to capture
- **Browser CDP integration** — Direct Chrome control via DevTools Protocol
- **Better prompts** — Few-shot examples for common tasks
- **More tests** — Target: 100+ unit tests

## Code Style

- Python 3.9+ compatible (no match/case, use `from __future__ import annotations`)
- Ruff for linting (configured in pyproject.toml)
- Docstrings for all public methods (Google style)
- Type hints for all function signatures

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_actions.py -v

# Run with coverage (if installed)
pytest tests/ -v --cov=src
```

## Important Notes

- **Never commit tokens** — `.gitignore` excludes token files, but double-check
- **Rate limits** — Be mindful when testing with real Copilot API
- **GPT-4o is free** — Use it as default model for testing (0 premium request cost)
- **PNG for images** — Always use PNG format for screenshots sent to Copilot API

## License

MIT — see [LICENSE](LICENSE) for details.
