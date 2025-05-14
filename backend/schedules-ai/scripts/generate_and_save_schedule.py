#!/usr/bin/env python3
"""
Script to generate and save a schedule.

This script generates a schedule using the scheduler and saves it to a JSON file.
"""

import asyncio
import os
import sys

# Add the parent directory to the path so we can import the src module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.scheduler import run_example_and_save

async def main():
    """Generate and save a schedule."""
    print("Generating and saving schedule...")
    result = await run_example_and_save()
    print(f"Schedule generated and saved with ID: {result.schedule_id}")
    print(f"File path: data/processed/schedule_{result.schedule_id}.json")

if __name__ == "__main__":
    asyncio.run(main())
