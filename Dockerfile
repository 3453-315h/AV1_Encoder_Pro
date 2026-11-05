# AV1 Video Encoder Pro - Docker Image
# Professional AV1 video encoding with FFmpeg and SVT-AV1
#
# USAGE:
#   Build:  docker build -t av1-encoder-pro .
#   Help:   docker run av1-encoder-pro --help
#   Encode: docker run -v /path/to/videos:/data av1-encoder-pro -i /data/input.mp4 -o /data/output.webm

FROM python:3.11-slim-bookworm

LABEL maintainer="AV1 Encoder Pro"
LABEL description="Professional AV1 Video Encoder with FFmpeg and SVT-AV1"
LABEL version="1.3.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    python3-tk \
    tk \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxft2 \
    libfontconfig1 \
    fonts-dejavu-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements*.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY av1core.py .
COPY era_search.py .
COPY av1_encoder_ctk.py .
COPY encode_cli.py .
COPY web_ui.py .
COPY assets/ ./assets/

# Copy entrypoint script
COPY entrypoint.sh .
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Create volumes for video files
RUN mkdir -p /videos /output
VOLUME ["/videos", "/output"]

# Expose web UI port
EXPOSE 2081

# Health check for Web mode
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os, sys, urllib.request; sys.exit(0 if os.environ.get('MODE') != 'web' else (0 if urllib.request.urlopen('http://127.0.0.1:2081/').getcode() == 200 else 1))"

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

