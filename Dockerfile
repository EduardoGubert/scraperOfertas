FROM python:3.11-slim

# Labels
LABEL maintainer="Eduardo - egnOfertas"
LABEL description="Scraper ML Afiliado com Playwright"

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
    # Para VNC/debug (opcional)
    x11vnc \
    xvfb \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia requirements e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala Playwright e browsers
# Instala Chrome REAL (menos detectável que Chromium) + Chromium como fallback
RUN playwright install chrome
RUN playwright install-deps chrome
RUN playwright install chromium
RUN playwright install-deps chromium

# Copia código
COPY scraper_ml_afiliado.py .
COPY api_ml_afiliado.py .

# Cria diretório para dados persistentes do browser
RUN mkdir -p /app/ml_browser_data && chmod 777 /app/ml_browser_data

# Volume para persistir cookies/sessão
VOLUME ["/app/ml_browser_data"]

# Expõe porta
EXPOSE 8000

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Comando de inicialização - Inicia Xvfb primeiro para ter display virtual real
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp & sleep 2 && uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000"]
