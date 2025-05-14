#!/usr/bin/env python3
"""
Script to run the development environment in a simple way.

This script generates an example schedule and then runs the API server.
"""

import os
import sys
import subprocess
import time

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Run the development environment."""
    print("Starting development environment...")
    
    # Generate an example schedule
    print("\n=== Generating Example Schedule ===")
    subprocess.run([sys.executable, os.path.join("scripts", "generate_example_schedule.py")])
    
    # Wait a bit
    time.sleep(1)
    
    # Run the API server
    print("\n=== Starting API Server ===")
    subprocess.run([sys.executable, os.path.join("scripts", "run_api_server.py")])

if __name__ == "__main__":
    main()
