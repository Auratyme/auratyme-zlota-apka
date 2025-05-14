#!/bin/bash
# Script to run the API server with JWT authentication enabled on Unix/Linux

echo "Starting API server with JWT authentication enabled..."

# Set environment variables
export ENABLE_JWT_AUTH=true
export DISABLE_DB=true

# Run the API server
python -m api.server

echo "API server stopped."
