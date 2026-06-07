# Hugging Face Docker Space - demo build (runs in DEMO_MODE, no secrets).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEMO_MODE=true \
    HOME=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user (uid 1000, as Hugging Face expects).
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user

EXPOSE 8501

CMD ["streamlit", "run", "app/main.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
