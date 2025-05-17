# Use an official Python runtime
FROM python:3.11-slim

WORKDIR /app

# Install Node.js
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify Node.js and npm installation
RUN node --version && npm --version

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory for cache files
RUN mkdir -p /app/data

# Copy your app code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Launch with Python
CMD ["python", "pia-discord-bot.py"]