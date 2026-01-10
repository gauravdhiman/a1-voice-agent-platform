# Backend Production Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies (including gobject/glib for LiveKit)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        pkg-config \
        libglib2.0-0 \
        libglib2.0-dev \
        libcairo2 \
        libcairo2-dev \
        libgirepository1.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy shared module (for production builds)
COPY shared/ /app/shared

# Copy application code
COPY backend/ /app

# Create non-root user
RUN addgroup --system --gid 1001 fastapi \
    && adduser --system --uid 1001 --gid 1001 --no-create-home fastapi \
    && chown -R fastapi:fastapi /app

# Switch to non-root user
USER fastapi

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application (without auto-instrumentation)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
