# Use official Python image
FROM python:3.11-slim

# Install Tesseract & Poppler
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose port
EXPOSE 8501

# Start Streamlit app
CMD ["streamlit", "run", "unified_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
