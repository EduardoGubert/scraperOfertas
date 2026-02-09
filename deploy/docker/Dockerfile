FROM python:3.11-slim

LABEL maintainer="Eduardo - egnOfertas"
LABEL description="scraperOfertas com FastAPI + Playwright + PostgreSQL + Redis"

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    xvfb \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY config/python/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r ./requirements.txt

RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

RUN mkdir -p /app/ml_browser_data /app/logs && chmod -R 777 /app/ml_browser_data /app/logs

VOLUME ["/app/ml_browser_data", "/app/logs"]

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
