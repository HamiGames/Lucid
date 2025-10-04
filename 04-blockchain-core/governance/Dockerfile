# LUCID BLOCKCHAIN-GOVERNANCES - SPEC-4 Compliant
FROM pickme/lucid:devcontainer-dind as base

LABEL org.lucid.plane="chain"
LABEL org.lucid.service="blockchain-governances"
LABEL org.lucid.stage="1"
LABEL org.lucid.expose="true"

WORKDIR /workspaces/Lucid

# Copy service-specific files
COPY . /workspaces/Lucid/04-blockchain-core/governance/

# Install dependencies
RUN cd 04-blockchain-core/governance && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    if [ -f package.json ]; then npm install; fi

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Entry point
EXPOSE 8080
CMD ["python", "04-blockchain-core/governance/main.py"]
