#!/usr/bin/env python3
"""
Test script for APIdog endpoints.

This script tests the APIdog endpoints by making requests to the API server.
"""

import requests
from pprint import pprint

# Base URL for the API server
BASE_URL = "http://localhost:8000/v1/apidog"

def test_list_schedules():
    """Test the endpoint to list all available schedules."""
    print("\n=== Testing List Schedules Endpoint ===")
    response = requests.get(f"{BASE_URL}/schedules")

    if response.status_code == 200:
        print("✅ Success! Status code:", response.status_code)
        schedules = response.json()
        print(f"Found {len(schedules)} schedules:")
        pprint(schedules)
        return schedules
    else:
        print("❌ Error! Status code:", response.status_code)
        print("Response:", response.text)
        return []

def test_get_schedule(schedule_id):
    """Test the endpoint to get a specific schedule."""
    print(f"\n=== Testing Get Schedule Endpoint (ID: {schedule_id}) ===")
    response = requests.get(f"{BASE_URL}/schedule/{schedule_id}")

    if response.status_code == 200:
        print("✅ Success! Status code:", response.status_code)
        schedule = response.json()
        print(f"Schedule has {len(schedule['tasks'])} tasks.")
        print("First 3 tasks:")
        for task in schedule['tasks'][:3]:
            print(f"  - {task['task']} ({task['start_time']} - {task['end_time']})")
    else:
        print("❌ Error! Status code:", response.status_code)
        print("Response:", response.text)

def test_get_latest_schedule():
    """Test the endpoint to get the latest schedule."""
    print("\n=== Testing Get Latest Schedule Endpoint ===")
    response = requests.get(f"{BASE_URL}/latest-schedule")

    if response.status_code == 200:
        print("✅ Success! Status code:", response.status_code)
        schedule = response.json()
        print(f"Latest schedule has {len(schedule['tasks'])} tasks.")
        print("First 3 tasks:")
        for task in schedule['tasks'][:3]:
            print(f"  - {task['task']} ({task['start_time']} - {task['end_time']})")
    else:
        print("❌ Error! Status code:", response.status_code)
        print("Response:", response.text)

def main():
    """Main function to run all tests."""
    print("Starting APIdog endpoints tests...")

    # Test listing schedules
    schedules = test_list_schedules()

    # Test getting a specific schedule if any are available
    if schedules:
        test_get_schedule(schedules[0]['schedule_id'])

    # Test getting the latest schedule
    test_get_latest_schedule()

    print("\nAll tests completed!")

if __name__ == "__main__":
    main()
