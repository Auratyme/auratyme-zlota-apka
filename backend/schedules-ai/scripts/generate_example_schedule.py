#!/usr/bin/env python3
"""
Script to generate an example schedule.

This script generates an example schedule and saves it to a JSON file.
"""

import json
import os
import sys
import uuid
from datetime import datetime

# Add the parent directory to the path so we can import the src module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generate_example_schedule():
    """Generate an example schedule."""
    schedule_id = str(uuid.uuid4())
    
    # Create an example schedule
    schedule = {
        "tasks": [
            {
                "start_time": "08:00",
                "end_time": "09:00",
                "task": "Morning Meeting"
            },
            {
                "start_time": "09:30",
                "end_time": "12:00",
                "task": "Project Work"
            },
            {
                "start_time": "12:00",
                "end_time": "13:00",
                "task": "Lunch Break"
            },
            {
                "start_time": "13:00",
                "end_time": "15:30",
                "task": "Development"
            },
            {
                "start_time": "15:30",
                "end_time": "16:00",
                "task": "Coffee Break"
            },
            {
                "start_time": "16:00",
                "end_time": "17:30",
                "task": "Code Review"
            }
        ]
    }
    
    # Create the data/processed directory if it doesn't exist
    os.makedirs(os.path.join("data", "processed"), exist_ok=True)
    
    # Save the schedule to a JSON file
    file_path = os.path.join("data", "processed", f"schedule_{schedule_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2, ensure_ascii=False)
    
    print(f"Example schedule generated with ID: {schedule_id}")
    print(f"Saved to: {file_path}")
    
    return schedule_id, file_path

if __name__ == "__main__":
    generate_example_schedule()
