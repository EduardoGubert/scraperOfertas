FROM python:3.11-slim

# Instala dependências do sistema para Playwright
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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia requirements e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn

# Instala Playwright e browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copia código
COPY scraper_ofertas.py .
COPY api_scraper.py .

# Expõe porta
EXPOSE 8000

# Comando de inicialização
CMD ["uvicorn", "api_scraper:app", "--host", "0.0.0.0", "--port", "8000"]
