#!/usr/bin/env python3
"""
Script to run the API server with JWT authentication enabled.

This script sets the ENABLE_JWT_AUTH environment variable to 'true' and runs the API server.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import the api module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["ENABLE_JWT_AUTH"] = "true"
os.environ["DISABLE_DB"] = "true"  # Set to "false" to enable database connection

def main():
    """Run the API server with JWT authentication enabled."""
    try:
        logger.info("Starting API server with JWT authentication enabled...")
        
        # Print current working directory and Python path
        logger.debug(f"Current working directory: {os.getcwd()}")
        logger.debug(f"Python path: {sys.path}")
        
        # Run the API server
        import uvicorn
        uvicorn.run(
            "api.server:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="debug",
        )
    except Exception as e:
        logger.exception(f"Error starting API server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
