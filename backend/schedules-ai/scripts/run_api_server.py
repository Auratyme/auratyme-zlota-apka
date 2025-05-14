#!/usr/bin/env python3
"""
Script to run the API server.

This script runs the API server using uvicorn.
"""

import uvicorn
import os
import sys

# Add the parent directory to the path so we can import the api module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Run the API server."""
    print("Starting API server...")
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

if __name__ == "__main__":
    main()
