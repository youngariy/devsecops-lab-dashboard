FROM python:3.12-slim

WORKDIR /app

# Pull latest Debian security fixes into the image layer used for scanning.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

EXPOSE 5000

CMD ["python", "src/main.py"]
