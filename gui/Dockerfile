FROM gcr.io/distroless/python3-debian12:arm64

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY gui/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r gui/requirements.txt

# Copy application code
COPY gui/ ./gui/
COPY gui-api-bridge/ ./gui-api-bridge/
COPY user-content/ ./user-content/
COPY RDP/ ./RDP/
COPY node/ ./node/
COPY contracts/ ./contracts/
COPY service-mesh/ ./service-mesh/
COPY electron-gui/ ./electron-gui/
COPY sessions/ ./sessions/
COPY service-mesh/ ./service-mesh/
COPY infrastructure/service-mesh/ ./infrastructure/service-mesh/
COPY infrastructure/kubernetes/ ./infrastructure/kubernetes/
COPY src/gui/ ./src/gui/

# Set non-root user for security
USER nonroot

# Expose port
EXPOSE 8000

# Run the application
CMD ["python3", "app/gui/entrypoint.py"]
