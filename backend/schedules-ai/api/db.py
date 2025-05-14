# === File: schedules-ai/api/db.py ===

"""
Database module for the API.

This module provides functions to connect to the PostgreSQL database and execute queries.
"""

import logging
import os
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)

# --- Database Connection ---
db_pool: Optional[asyncpg.Pool] = None

async def init_db_pool():
    """
    Initialize the database connection pool.

    Returns:
        The database connection pool.

    Raises:
        Exception: If connection to the database fails.
    """
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            user=os.environ.get("DB_USERNAME", "postgres"),
            password=os.environ.get("DB_PASSWORD", "postgres"),
            database=os.environ.get("DB_NAME", "schedules"),
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", 5432))
        )
        logger.info("✅ Connected to PostgreSQL database.")
        return db_pool
    except Exception as e:
        logger.error(f"❌ Error connecting to PostgreSQL: {e}")
        raise


async def close_db_pool():
    """Close the database connection pool."""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed.")


async def get_db_pool():
    """
    Get the database connection pool. Initialize it if it doesn't exist.

    Returns:
        The database connection pool.
    """
    global db_pool
    if db_pool is None:
        await init_db_pool()
    return db_pool

# --- Schedule Operations ---

async def save_schedule_to_db(schedule_id, user_id, target_date, schedule_data):
    """
    Save a schedule to the database.

    Args:
        schedule_id: The ID of the schedule.
        user_id: The ID of the user.
        target_date: The target date of the schedule.
        schedule_data: The schedule data as a JSON object.

    Returns:
        True if the schedule was saved successfully, False otherwise.
    """
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO schedules (
                    schedule_id,
                    user_id,
                    target_date,
                    schedule_data
                ) VALUES (
                    $1, $2, $3, $4
                )
                ON CONFLICT (schedule_id) DO UPDATE SET
                    user_id = $2,
                    target_date = $3,
                    schedule_data = $4
            """,
            str(schedule_id),
            str(user_id) if user_id else None,
            target_date,
            schedule_data)
        logger.info(f"Schedule {schedule_id} saved to database.")
        return True
    except Exception as e:
        logger.error(f"Error saving schedule to database: {e}")
        return False

async def get_schedule_from_db(schedule_id):
    """
    Get a schedule from the database.

    Args:
        schedule_id: The ID of the schedule.

    Returns:
        The schedule data as a JSON object, or None if not found.
    """
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT schedule_data
                FROM schedules
                WHERE schedule_id = $1
            """, str(schedule_id))

            if result:
                return result['schedule_data']
            return None
    except Exception as e:
        logger.error(f"Error getting schedule from database: {e}")
        return None


async def list_schedules_from_db():
    """
    List all schedules from the database.

    Returns:
        A list of schedule IDs.
    """
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT schedule_id
                FROM schedules
                ORDER BY created_at DESC
            """)

            return [{'schedule_id': row['schedule_id']} for row in results]
    except Exception as e:
        logger.error(f"Error listing schedules from database: {e}")
        return []


async def get_latest_schedule_from_db():
    """
    Get the latest schedule from the database.

    Returns:
        The schedule data as a JSON object, or None if not found.
    """
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT schedule_data
                FROM schedules
                ORDER BY created_at DESC
                LIMIT 1
            """)

            if result:
                return result['schedule_data']
            return None
    except Exception as e:
        logger.error(f"Error getting latest schedule from database: {e}")
        return None


# --- User Schedule Operations ---

async def list_schedules_from_db_by_user_id(user_id):
    """
    List all schedules for a user from the database.

    Args:
        user_id: The ID of the user.

    Returns:
        A list of schedules.
    """
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT schedule_data
                FROM user_schedules
                WHERE user_id = $1
                ORDER BY created_at DESC
            """, str(user_id))

            return [row['schedule_data'] for row in results]
    except Exception as e:
        logger.error(f"Error listing schedules from database: {e}")
        return []


async def delete_schedule_from_db(schedule_id, user_id):
    """
    Delete a schedule from the database.

    Args:
        schedule_id: The ID of the schedule.
        user_id: The ID of the user.

    Returns:
        True if the schedule was deleted, False otherwise.
    """
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM user_schedules
                WHERE schedule_id = $1 AND user_id = $2
            """, str(schedule_id), str(user_id))

            return result == "DELETE 1"
    except Exception as e:
        logger.error(f"Error deleting schedule from database: {e}")
        return False

# --- Database Schema ---

async def create_tables():
    """
    Create the necessary database tables if they don't exist.

    Raises:
        Exception: If table creation fails.
    """
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    schedule_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    target_date DATE,
                    schedule_data JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_schedules (
                    schedule_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    schedule_data JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)

            logger.info("Database tables created or already exist.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
