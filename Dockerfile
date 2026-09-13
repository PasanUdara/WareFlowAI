# WareFlow AI - Container Dockerfile
# Python 3.10 Slim base image
FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    SDL_VIDEODRIVER=dummy \
    SDL_AUDIODRIVER=dummy

# Set working directory
WORKDIR /app



# Install Python dependencies first for efficient layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create a non-root user for security
RUN groupadd -g 1000 wareflow && \
    useradd -u 1000 -g wareflow -m -s /bin/bash wareflow

# Copy application source code
COPY . .

# Ensure proper permissions for the non-root user
RUN chown -R wareflow:wareflow /app

# Switch to non-root user
USER wareflow

# Expose FastAPI gateway port
EXPOSE 8000

# Container healthcheck (uses Python instead of curl to avoid apt-get dependency)
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command: launch FastAPI server with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
