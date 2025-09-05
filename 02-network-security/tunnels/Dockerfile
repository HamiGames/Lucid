FROM alpine:3.20

# Install curl for SOCKS5 testing
RUN apk add --no-cache curl bash

WORKDIR /app

# Copy verification script
COPY verify_tunnel.sh /app/verify_tunnel.sh
RUN chmod +x /app/verify_tunnel.sh

ENTRYPOINT ["/app/verify_tunnel.sh"]
