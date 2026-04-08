FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for some python packages
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies using standard pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project files
COPY . .

# Critical: Ensure Python can find environment.py in the root
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose the port Hugging Face expects
EXPOSE 7860

# Use python -m uvicorn directly (guaranteed to be in PATH after pip install)
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]