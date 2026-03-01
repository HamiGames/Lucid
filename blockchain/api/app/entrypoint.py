#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blockchain Engine Entrypoint
UTF-8 encoded entrypoint script for distroless container

This script serves as the entrypoint for the blockchain-engine container,
avoiding complex JSON array quoting issues and encoding problems.
"""
import os
import sys

if __name__ == "__main__":
    port = int(os.getenv('BLOCKCHAIN_ENGINE_PORT', '8084'))
    # Always bind to 0.0.0.0 to allow healthchecks and external access
    # This ensures the service is accessible from localhost inside the container
    host = '0.0.0.0'
    
    import uvicorn
    uvicorn.run('api.app.main:app', host=host, port=port)

