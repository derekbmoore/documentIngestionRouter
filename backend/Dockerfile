FROM python:3.11-slim

WORKDIR /app

# System dependencies for extraction engines
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model for entity extraction
RUN python -m spacy download en_core_web_sm

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run
ENV PYTHONPATH=/app
EXPOSE 8082
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8082"]
