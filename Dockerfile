# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a simple health check script
RUN echo "#!/bin/bash\necho 'CorpExpenseAudit is ready for deployment'" > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# Expose port for Hugging Face Spaces
EXPOSE 7860

# Default command - can be overridden
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
