#!/usr/bin/env python3
"""
Test script for APIdog endpoints with database support.

This script tests the APIdog endpoints by making requests to the API server
and verifies that the database integration works correctly.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import date
from pprint import pprint

# Add the parent directory to the path so we can import the api module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.db import init_db_pool, create_tables, save_schedule_to_db, get_schedule_from_db, list_schedules_from_db, get_latest_schedule_from_db, close_db_pool

# Test data
TEST_SCHEDULE = {
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
        }
    ]
}

async def test_db_connection():
    """Test the database connection."""
    print("\n=== Testing Database Connection ===")
    try:
        await init_db_pool()
        await create_tables()
        print("✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def test_save_schedule():
    """Test saving a schedule to the database."""
    print("\n=== Testing Save Schedule to Database ===")
    schedule_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    target_date = date.today()
    
    try:
        result = await save_schedule_to_db(schedule_id, user_id, target_date, TEST_SCHEDULE)
        if result:
            print(f"✅ Schedule saved to database with ID: {schedule_id}")
            return schedule_id
        else:
            print("❌ Failed to save schedule to database")
            return None
    except Exception as e:
        print(f"❌ Error saving schedule to database: {e}")
        return None

async def test_get_schedule(schedule_id):
    """Test getting a schedule from the database."""
    print(f"\n=== Testing Get Schedule from Database (ID: {schedule_id}) ===")
    try:
        schedule_data = await get_schedule_from_db(schedule_id)
        if schedule_data:
            print("✅ Schedule retrieved from database!")
            print("Schedule data:")
            pprint(schedule_data)
            return True
        else:
            print("❌ Schedule not found in database")
            return False
    except Exception as e:
        print(f"❌ Error getting schedule from database: {e}")
        return False

async def test_list_schedules():
    """Test listing schedules from the database."""
    print("\n=== Testing List Schedules from Database ===")
    try:
        schedules = await list_schedules_from_db()
        print(f"✅ Found {len(schedules)} schedules in database:")
        pprint(schedules)
        return schedules
    except Exception as e:
        print(f"❌ Error listing schedules from database: {e}")
        return []

async def test_get_latest_schedule():
    """Test getting the latest schedule from the database."""
    print("\n=== Testing Get Latest Schedule from Database ===")
    try:
        schedule_data = await get_latest_schedule_from_db()
        if schedule_data:
            print("✅ Latest schedule retrieved from database!")
            print("Schedule data:")
            pprint(schedule_data)
            return True
        else:
            print("❌ Latest schedule not found in database")
            return False
    except Exception as e:
        print(f"❌ Error getting latest schedule from database: {e}")
        return False

async def main():
    """Main function to run all tests."""
    print("Starting APIdog database tests...")
    
    # Test database connection
    db_connected = await test_db_connection()
    if not db_connected:
        print("❌ Cannot continue tests without database connection.")
        return
    
    # Test saving a schedule
    schedule_id = await test_save_schedule()
    if not schedule_id:
        print("❌ Cannot continue tests without saving a schedule.")
        return
    
    # Test getting a schedule
    await test_get_schedule(schedule_id)
    
    # Test listing schedules
    await test_list_schedules()
    
    # Test getting the latest schedule
    await test_get_latest_schedule()
    
    # Close database connection
    await close_db_pool()
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
