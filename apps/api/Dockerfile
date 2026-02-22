FROM python:3.12-slim

WORKDIR /app

# Pull latest Debian security fixes into the image layer used for scanning.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
RUN useradd --system --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser
ENV APP_HOST=0.0.0.0
ENV APP_PORT=5000

EXPOSE 5000

CMD ["python", "src/main.py"]
