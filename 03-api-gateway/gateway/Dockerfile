FROM python:3.12-slim

# Install system deps
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements if available
COPY requirements.txt .
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy source
COPY . .

EXPOSE 8080

# Default command: run FastAPI (or placeholder HTTP server if no code yet)
CMD ["python", "-m", "http.server", "8080"]
