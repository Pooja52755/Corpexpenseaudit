# Multi-stage build for CorpExpenseAudit OpenEnv Environment
# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Set PATH for pip packages
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Copy project files
COPY . /app/

# Verify critical files exist
RUN test -f /app/api.py && \
    test -f /app/models.py && \
    test -f /app/environment.py && \
    test -f /app/inference.py && \
    echo "✓ All required files present"

# Create health check script
RUN mkdir -p /app/scripts && \
    echo "#!/bin/bash" > /app/scripts/healthcheck.sh && \
    echo "curl -f http://localhost:7860/health || exit 1" >> /app/scripts/healthcheck.sh && \
    chmod +x /app/scripts/healthcheck.sh

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/scripts/healthcheck.sh

# Expose port for Hugging Face Spaces
EXPOSE 7860

# Default command - start FastAPI server
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860", "--reload"]
