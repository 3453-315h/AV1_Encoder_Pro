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
LABEL version="1.1.0"

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
COPY requirements.txt .
RUN pip install --no-cache-dir customtkinter>=5.0.0 Pillow>=9.0.0 gradio>=4.0.0

# Copy application files
COPY av1_encoder_ctk.py .
COPY encode_cli.py .
COPY web_ui.py .
COPY assets/ ./assets/

# Copy entrypoint script
COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

# Create volumes for video files
RUN mkdir -p /videos /output
VOLUME ["/videos", "/output"]

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

