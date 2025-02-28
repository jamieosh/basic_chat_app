# AI Chat Application

A modern, responsive chat application built with Python FastAPI and HTMX that provides an interactive interface for conversing with AI models.

## Features

- 🚀 Real-time chat interface with AI
- 💬 Multi-line message input with auto-resize
- 🎨 Modern, responsive UI with Tailwind CSS
- ⚡ Fast, lightweight interactions using HTMX
- 📱 Mobile-friendly design
- 🔄 Smooth animations and typing indicators
- 🎯 Error handling and rate limiting
- 📝 Code block formatting support
- ⏰ Message timestamps
- 🔧 Configurable system prompts and context

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd podcast_chat
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

5. Run the application:
```bash
uvicorn main:app --reload
```

The application will be available at `http://localhost:8000`

## Dependencies

- Python 3.7+
- FastAPI
- HTMX
- Tailwind CSS
- OpenAI Python Client
- Jinja2
- python-dotenv

## Project Structure

```
podcast_chat/
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
└── requirements.txt    # Python dependencies
```

## Development

### Adding New Features

1. **New Agent Types**: Extend the `BaseAgent` class in `agents/base_agent.py`
2. **Custom Prompts**: Add new templates in `templates/prompts/<agent_type>/`
3. **UI Components**: Add new components in `templates/components/`

### Configuration

- Logging configuration can be modified in `utils/logging_config.py`
- Prompt templates can be customized in `templates/prompts/`
- UI styling can be adjusted in `static/css/chat.css`

### Best Practices

- Keep the single responsibility principle in mind
- Add appropriate logging for debugging
- Follow the established error handling patterns
- Write clear documentation for new features

## License

[MIT License](LICENSE)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
