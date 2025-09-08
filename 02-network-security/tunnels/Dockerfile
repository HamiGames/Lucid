# Path: 02-network-security/tunnels/Dockerfile
# Tunnel service (manages onion + validation)

FROM python:3.12-alpine

WORKDIR /app

# Install tools
RUN apk add --no-cache bash curl netcat-openbsd socat xxd

# Install Python dependencies
RUN pip install --no-cache-dir requests[socks]

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 7000

ENTRYPOINT ["/app/entrypoint.sh"]
