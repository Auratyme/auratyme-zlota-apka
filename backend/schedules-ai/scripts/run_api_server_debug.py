#!/usr/bin/env python3
"""
Script to run the API server in debug mode.

This script runs the API server using uvicorn with debug logging.
"""

import uvicorn
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

def main():
    """Run the API server in debug mode."""
    try:
        logger.info("Starting API server in debug mode...")
        
        # Print current working directory and Python path
        logger.debug(f"Current working directory: {os.getcwd()}")
        logger.debug(f"Python path: {sys.path}")
        
        # Check if the api module can be imported
        try:
            import api
            logger.debug(f"API module found at: {api.__file__}")
        except ImportError as e:
            logger.error(f"Error importing api module: {e}")
            sys.exit(1)
        
        # Check if the api.server module can be imported
        try:
            import api.server
            logger.debug(f"API server module found at: {api.server.__file__}")
        except ImportError as e:
            logger.error(f"Error importing api.server module: {e}")
            sys.exit(1)
        
        # Run the API server
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
