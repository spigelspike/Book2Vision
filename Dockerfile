FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (tesseract, etc.)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install fastapi uvicorn python-multipart

# Download Spacy model
RUN python -m spacy download en_core_web_sm

# Copy code
COPY . .

# Expose port
EXPOSE 8000

# Run
CMD ["python", "src/server.py"]
