FROM gcr.io/distroless/python3-debian12:arm64

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY gui/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r gui/requirements.txt

# Copy application code
COPY gui/ /app/gui/

# Set non-root user for security
USER nonroot

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
