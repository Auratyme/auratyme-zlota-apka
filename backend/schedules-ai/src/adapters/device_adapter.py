"""
Adapter for Wearable Device Data Integration.

Provides a unified interface (protocol) and one or more concrete implementations
(e.g., MockDeviceDataAdapter) to fetch health/activity data from wearable platforms.
"""

import logging
import random
from abc import abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Protocol, List, Optional, Tuple # Added Tuple
from uuid import UUID

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Enumeration of supported wearable data sources."""
    FITBIT = "fitbit"
    GARMIN = "garmin"
    OURA = "oura"
    APPLE_HEALTH = "apple_health"
    GOOGLE_FIT = "google_fit"
    MOCK = "mock"       # For testing/development
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SleepDataRecord:
    """Represents data for a single sleep session."""
    start_time: datetime
    end_time: datetime
    duration: timedelta
    efficiency: Optional[float] = None
    source: DataSource = DataSource.UNKNOWN
    source_record_id: Optional[str] = None

    def __post_init__(self):
        if self.start_time.tzinfo is None or self.end_time.tzinfo is None:
            logger.warning(
                "SleepDataRecord created with naive datetimes. "
                "Timezone-aware datetimes are recommended."
            )
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")


@dataclass(frozen=True)
class HeartRateDataPoint:
    """Represents a single heart rate measurement."""
    timestamp: datetime
    bpm: int


@dataclass(frozen=True)
class HrvDataPoint:
    """Represents a single HRV measurement."""
    timestamp: datetime
    rmssd_ms: Optional[float] = None
    sdrr_ms: Optional[float] = None


@dataclass(frozen=True)
class ActivityDataSummary:
    """Represents a daily activity summary."""
    date: date
    steps: Optional[int] = None
    active_minutes: Optional[int] = None
    calories_burned: Optional[float] = None
    source: DataSource = DataSource.UNKNOWN
    source_record_id: Optional[str] = None


class DeviceAdapterProtocol(Protocol):
    """Defines the interface expected from any device adapter."""

    @abstractmethod
    async def get_sleep_data(
        self, user_id: UUID, start_date: date, end_date: date, source: DataSource
    ) -> List[SleepDataRecord]:
        ...

    @abstractmethod
    async def get_heart_rate_data(
        self, user_id: UUID, start_datetime: datetime, end_datetime: datetime, source: DataSource
    ) -> List[HeartRateDataPoint]:
        ...

    @abstractmethod
    async def get_hrv_data(
        self, user_id: UUID, start_datetime: datetime, end_datetime: datetime, source: DataSource
    ) -> List[HrvDataPoint]:
        ...

    @abstractmethod
    async def get_activity_summary(
        self, user_id: UUID, target_date: date, source: DataSource
    ) -> Optional[ActivityDataSummary]:
        ...


class DeviceDataAdapter:
    """
    Main device adapter class that implements the DeviceAdapterProtocol.
    This class can be configured to use different adapters based on the configuration.
    """

    def __init__(self, config=None):
        self.config = config or {}
        logger.info("DeviceDataAdapter initialized.")
        # By default, use the MockDeviceDataAdapter for development/testing
        self.adapter = MockDeviceDataAdapter()

    async def get_sleep_data(
        self, user_id: UUID, start_date: date, end_date: date, source: DataSource
    ) -> List[SleepDataRecord]:
        """Delegates to the configured adapter to get sleep data."""
        return await self.adapter.get_sleep_data(user_id, start_date, end_date, source)

    async def get_heart_rate_data(
        self, user_id: UUID, start_datetime: datetime, end_datetime: datetime, source: DataSource
    ) -> List[HeartRateDataPoint]:
        """Delegates to the configured adapter to get heart rate data."""
        return await self.adapter.get_heart_rate_data(user_id, start_datetime, end_datetime, source)

    async def get_hrv_data(
        self, user_id: UUID, start_datetime: datetime, end_datetime: datetime, source: DataSource
    ) -> List[HrvDataPoint]:
        """Delegates to the configured adapter to get HRV data."""
        return await self.adapter.get_hrv_data(user_id, start_datetime, end_datetime, source)

    async def get_activity_summary(
        self, user_id: UUID, target_date: date, source: DataSource
    ) -> Optional[ActivityDataSummary]:
        """Delegates to the configured adapter to get activity summary."""
        return await self.adapter.get_activity_summary(user_id, target_date, source)


class MockDeviceDataAdapter(DeviceAdapterProtocol):
    """
    Mock implementation of the DeviceAdapterProtocol for testing/development.
    Generates random data rather than calling any real API.
    """

    def __init__(self) -> None:
        logger.info("MockDeviceDataAdapter initialized.")

    async def get_sleep_data(
        self, user_id: UUID, start_date: date, end_date: date, source: DataSource
    ) -> List[SleepDataRecord]:
        """Generates mock sleep data for the specified date range."""
        if source != DataSource.MOCK:
            logger.warning(f"MockDeviceDataAdapter called for non-MOCK source: {source}. Returning empty list.")
            return []

        mock_records: List[SleepDataRecord] = []
        current_date = start_date
        while current_date <= end_date:
            # Simulate one sleep session per night (can be made more complex)
            try:
                # Random bedtime between 21:00 and 01:00
                bed_hour = random.randint(21, 25) # 21 to 25 (1 AM next day)
                bed_minute = random.randint(0, 59)
                bed_dt_naive = datetime.combine(current_date, time(hour=bed_hour % 24, minute=bed_minute))
                if bed_hour >= 24: bed_dt_naive -= timedelta(days=1) # Adjust date if bedtime is past midnight

                # Random duration between 6 and 9.5 hours
                duration_hours = random.uniform(6.0, 9.5)
                duration = timedelta(hours=duration_hours)

                # Calculate end time
                end_dt_naive = bed_dt_naive + duration

                # Make timezone-aware (assuming UTC for mock data consistency)
                start_time_utc = bed_dt_naive.replace(tzinfo=timezone.utc)
                end_time_utc = end_dt_naive.replace(tzinfo=timezone.utc)

                # Random efficiency
                efficiency = random.uniform(0.75, 0.98)

                record = SleepDataRecord(
                    start_time=start_time_utc,
                    end_time=end_time_utc,
                    duration=duration,
                    efficiency=efficiency,
                    source=DataSource.MOCK,
                    source_record_id=f"mock_sleep_{current_date.isoformat()}"
                )
                mock_records.append(record)
                logger.debug(f"Generated mock sleep record for {current_date}: {record.start_time} - {record.end_time}")
            except Exception as e:
                 logger.error(f"Error generating mock sleep data for {current_date}: {e}")

            current_date += timedelta(days=1)

        return mock_records

    async def get_heart_rate_data(
        self, user_id: UUID, start_datetime: datetime, end_datetime: datetime, source: DataSource
    ) -> List[HeartRateDataPoint]:
        """Generates mock heart rate data points within the specified datetime range."""
        if source != DataSource.MOCK:
            logger.warning(f"MockDeviceDataAdapter called for non-MOCK source: {source}. Returning empty list.")
            return []

        mock_points: List[HeartRateDataPoint] = []
        current_time = start_datetime
        # Generate data points roughly every 5-15 minutes
        while current_time < end_datetime:
            try:
                # Simulate typical resting/sleeping HR range
                bpm = random.randint(45, 75)
                # Ensure timestamp is timezone-aware (use input timezone or default to UTC)
                ts = current_time.replace(tzinfo=current_time.tzinfo or timezone.utc)
                mock_points.append(HeartRateDataPoint(timestamp=ts, bpm=bpm))

                # Advance time by a random interval
                current_time += timedelta(minutes=random.randint(5, 15))
            except Exception as e:
                 logger.error(f"Error generating mock HR data point around {current_time}: {e}")
                 # Advance time anyway to avoid infinite loop on error
                 current_time += timedelta(minutes=10)


        logger.debug(f"Generated {len(mock_points)} mock heart rate data points between {start_datetime} and {end_datetime}.")
        return mock_points

    async def get_hrv_data(
        self, user_id: UUID, start_datetime: datetime, end_datetime: datetime, source: DataSource
    ) -> List[HrvDataPoint]:
        """Generates mock HRV data points (RMSSD) within the specified datetime range."""
        if source != DataSource.MOCK:
            logger.warning(f"MockDeviceDataAdapter called for non-MOCK source: {source}. Returning empty list.")
            return []

        mock_points: List[HrvDataPoint] = []
        current_time = start_datetime
        # Generate data points roughly every 15-45 minutes
        while current_time < end_datetime:
             try:
                # Simulate typical RMSSD range during sleep/rest (in ms)
                rmssd = random.uniform(25.0, 80.0)
                # Ensure timestamp is timezone-aware
                ts = current_time.replace(tzinfo=current_time.tzinfo or timezone.utc)
                mock_points.append(HrvDataPoint(timestamp=ts, rmssd_ms=rmssd))

                # Advance time by a random interval
                current_time += timedelta(minutes=random.randint(15, 45))
             except Exception as e:
                 logger.error(f"Error generating mock HRV data point around {current_time}: {e}")
                 current_time += timedelta(minutes=30)

        logger.debug(f"Generated {len(mock_points)} mock HRV data points between {start_datetime} and {end_datetime}.")
        return mock_points

    async def get_activity_summary(
        self, user_id: UUID, target_date: date, source: DataSource
    ) -> Optional[ActivityDataSummary]:
        """Generates a mock daily activity summary."""
        if source != DataSource.MOCK:
            logger.warning(f"MockDeviceDataAdapter called for non-MOCK source: {source}. Returning None.")
            return None

        try:
            steps = random.randint(2000, 15000)
            active_minutes = random.randint(15, 120)
            calories = random.uniform(1800.0, 3500.0)

            summary = ActivityDataSummary(
                date=target_date,
                steps=steps,
                active_minutes=active_minutes,
                calories_burned=calories,
                source=DataSource.MOCK,
                source_record_id=f"mock_activity_{target_date.isoformat()}"
            )
            logger.debug(f"Generated mock activity summary for {target_date}: {summary}")
            return summary
        except Exception as e:
             logger.error(f"Error generating mock activity summary for {target_date}: {e}")
             return None
