FROM python:3.11-slim

# Install system dependencies for Pillow, ReportLab, pdf2docx, LibreOffice (Office->PDF), and MS-compatible fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libglib2.0-0 \
    libgomp1 \
    fontconfig \
    fonts-dejavu \
    fonts-liberation \
    fonts-crosextra-carlito \
    fonts-crosextra-caladea \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    && fc-cache -f \
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