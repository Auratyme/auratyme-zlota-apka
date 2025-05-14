#!/usr/bin/env python3
"""
Script to run the development environment.

This script runs both the scheduler and the API server in separate processes.
"""

import os
import sys
import time
import subprocess
import threading
import signal

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_scheduler():
    """Run the scheduler in a separate process."""
    print("Starting scheduler...")
    scheduler_process = subprocess.Popen(
        ["python", "-m", "src.core.scheduler"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    
    # Print scheduler output in real-time
    for line in scheduler_process.stdout:
        print(f"[SCHEDULER] {line.strip()}")
    
    return scheduler_process

def run_api_server():
    """Run the API server in a separate process."""
    print("Starting API server...")
    api_process = subprocess.Popen(
        ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    
    # Print API server output in real-time
    for line in api_process.stdout:
        print(f"[API SERVER] {line.strip()}")
    
    return api_process

def main():
    """Run both the scheduler and the API server."""
    print("Starting development environment...")
    
    # Start scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # Start API server in the main thread
    api_process = None
    try:
        # Wait a bit for the scheduler to start
        time.sleep(2)
        api_process = run_api_server()
        api_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        if api_process:
            api_process.terminate()
    
    print("Development environment stopped.")

if __name__ == "__main__":
    main()
