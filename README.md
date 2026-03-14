# Python-First LLM Chat Workbench

A lightweight FastAPI + HTMX project for quickly experimenting with LLM chat behavior in Python.

This repository is intentionally a workbench, not a full-featured production chat platform. It is designed to be usable out of the box while staying easy to fork and extend.

## Vision And Roadmap

- Vision charter: `plans/VISION.md`
- Phase model: `plans/PHASES.md`

Those documents define the long-term direction and maturity phases. This README focuses on current usage and contributor workflow.

## Current Capability (Today)

- Server-rendered web chat UI with HTMX interactions.
- Single-turn request/response chat flow.
- OpenAI-backed agent implementation (`gpt-4o-mini` by default).
- Prompt-template-driven system and user prompt construction.
- Neutral `AI Chat` defaults with no implicit domain context or memory.
- Safe HTML rendering with fenced code block formatting.
- Responsive frontend suitable for desktop and mobile.

## Near-Term Product Shape

- Keep the core simple and predictable.
- Maintain a Python-first, minimal-JavaScript approach.
- Preserve obvious extension seams for model, memory, and tool experimentation.

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd basic_chat_app
```

2. Use Python 3.13+ and sync dependencies with `uv`:
```bash
uv sync
```

3. Create a `.env` file in the project root and add your OpenAI API key:
```dotenv
OPENAI_API_KEY=your_api_key_here
```

4. Run the application:
```bash
uv run uvicorn main:app --reload
```

The application will be available at `http://localhost:8000`.

## Dependencies

- Python 3.13+
- FastAPI
- HTMX
- OpenAI Python Client
- Jinja2
- python-dotenv

## Project Structure

```
basic_chat_app/
├── agents/                 # AI agent implementations
│   ├── base_agent.py      # Abstract base agent class
│   └── openai_agent.py    # OpenAI-specific agent implementation
├── static/                # Static assets
│   ├── css/              # CSS styles
│   └── js/               # JavaScript files
├── templates/            # HTML templates
│   ├── components/       # Reusable components
│   └── prompts/         # AI prompt templates
├── utils/               # Utility functions
│   ├── html_formatter.py
│   ├── logging_config.py
│   └── prompt_manager.py
├── main.py             # FastAPI application
├── pyproject.toml      # Project metadata and dependencies
└── uv.lock             # Locked dependency versions for uv
```

## Development

Dependency source of truth:
- `pyproject.toml` + `uv.lock`

Run tests with:
```bash
uv run python -m pytest
```

Install Playwright Chromium (required for `tests/e2e/test_chat_smoke.py`):
```bash
uv run playwright install chromium
```

Run the frontend smoke test only:
```bash
uv run python -m pytest tests/e2e -q
```

Run lint and type checks:
```bash
uv run ruff check .
uv run mypy .
```

Install git hooks:
```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

### Adding New Features

1. **New Agent Types**: Extend the `BaseAgent` class in `agents/base_agent.py`
2. **Custom Prompts**: Add new templates in `templates/prompts/<agent_type>/`
3. **UI Components**: Add new components in `templates/components/`

### Configuration

- Logging configuration can be modified in `utils/logging_config.py`
- Prompt templates can be customized in `templates/prompts/`
- UI styling can be adjusted in `static/css/chat.css`

### Baseline Defaults

- The default assistant identity is `AI Chat`.
- The default chat request uses a fixed prompt name and `temperature=0.0`.
- The default system prompt is generic.
- The default user-context prompt remains available as a customization seam, but contributes nothing unless you explicitly add context variables or edit the template.
- The app does not keep multi-turn memory in Phase 1; each request is handled independently.

### Best Practices

- Keep structure and APIs straightforward.
- Prefer small, localized changes over broad rewrites.
- Follow established error handling and logging patterns.
- Add or update tests with behavior changes.
- Keep docs aligned with `plans/VISION.md` and `plans/PHASES.md`.

## License

[MIT License](LICENSE)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
