# Use an official Python runtime
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory for cache files
RUN mkdir -p /app/data

# Copy your app code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Launch with Gunicorn on port 5000
CMD ["python", "pia-discord-bot.py"]
