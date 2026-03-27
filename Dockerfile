# Use official Python image
FROM python:3.11-slim

# Install system dependencies for Zola and PDF processing
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Zola
RUN curl -L https://github.com/getzola/zola/releases/download/v0.18.0/zola-v0.18.0-x86_64-unknown-linux-gnu.tar.gz | tar xz -C /usr/local/bin

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Environment variables for Agents
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434
ENV SRE_HIL_MODE=optional

# Expose port for local testing (if needed)
EXPOSE 8080

# Default command: Run the orchestrator to harvest and generate
CMD ["python", "agents/orchestrator/orchestrator.py"]
