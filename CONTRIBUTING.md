# Contributing to LLM Session API

## Development Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/yourusername/llm-session-api.git
   ```

2. **Setup Environment**
   ```bash
   cp .env.example .env
   docker-compose up --build
   ```

## Pull Request Guidelines

1. **Atomic Commits**: Keep commits small and focused.
2. **No Secrets**: Ensure you have not accidentally committed your `.env` file or the `session_data/` folder.
