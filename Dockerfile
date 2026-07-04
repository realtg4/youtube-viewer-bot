# Dockerfile for YouTube Viewer Bot
FROM python:3.11-slim

# Install system dependencies (including xvfb for headful browser emulation)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome using modern, secure keyrings (fixing apt-key missing error)
RUN mkdir -p /etc/apt/keyrings \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create directories for Chrome profiles
RUN mkdir -p /app/chrome_profiles && chmod 755 /app/chrome_profiles

# Set environment variables
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# Expose port (Matches Render's default routing if using the Dummy Server hack)
EXPOSE 10000

# Start command
CMD ["python", "main.py"]