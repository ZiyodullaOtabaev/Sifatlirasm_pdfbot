FROM python:3.11-slim

# Install system dependencies for Pillow, ReportLab, and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment defaults
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "bot.main"]