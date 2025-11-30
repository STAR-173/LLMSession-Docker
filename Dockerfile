# Base Image
FROM python:3.11-slim

# Environment Configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    XDG_DATA_HOME=/root/.local/share

# Install System Dependencies (Xvfb is kept for headless=False execution)
RUN apt-get update && apt-get install -y \
    xvfb \
    curl \
    build-essential \
    libgtk-3-0 \
    libasound2 \
    libgbm1 \
    libnss3 \
    libxss1 \
    libxtst6 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# App Code
COPY app ./app
COPY scripts ./scripts
RUN chmod +x ./scripts/start.sh

# Persistence & Output Dirs
RUN mkdir -p /root/.local/share/LLMSession
RUN mkdir -p /app/output

EXPOSE 8000

ENTRYPOINT ["./scripts/start.sh"]