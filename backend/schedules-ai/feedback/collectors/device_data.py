# === File: scheduler-core/feedback/collectors/device_data.py ===

"""
Device Data Feedback Collector.

Collects processed data from wearable devices or other health platforms
(e.g., sleep analysis, activity summaries) via the WearableService.
This collected data is intended for storage and later use in analyzing
schedule effectiveness, adapting models, and providing insights back to the user.
"""

import json
import logging
import random
from dataclasses import asdict, dataclass, field
from datetime import time, date, datetime, timedelta, timezone
from typing import Any, Dict, Optional, List
from uuid import UUID, uuid4

from src.adapters.device_adapter import DataSource  # <-- Import DataSource here
from src.services.wearables import ProcessedWearableData, WearableService

logger = logging.getLogger(__name__)


@dataclass
class StoredDeviceData:
    """
    Represents processed device data structured for storage and analysis.
    Required fields (user_id, target_date, data_source) must be provided upon instantiation.
    Fields with default values are automatically populated if not provided.
    """
    # Required fields (no default values)
    user_id: UUID
    target_date: date
    data_source: str

    # Fields with default values
    record_id: UUID = field(default_factory=uuid4)
    processed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sleep_quality_score: Optional[float] = None
    actual_sleep_duration_minutes: Optional[float] = None
    sleep_onset_time_utc: Optional[datetime] = None
    sleep_offset_time_utc: Optional[datetime] = None
    sleep_deficit_minutes: Optional[float] = None
    resting_hr_avg_bpm: Optional[float] = None
    hrv_avg_rmssd_ms: Optional[float] = None
    steps: Optional[int] = None
    active_minutes: Optional[int] = None
    calories_burned: Optional[float] = None
    raw_data_reference: Optional[str] = None


class DeviceDataCollector:
    """
    Collects and prepares processed wearable data for storage.
    """

    def __init__(
        self,
        wearable_service: WearableService,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not isinstance(wearable_service, WearableService):
            logger.warning("WearableService is not a valid instance.")
        self.wearable_service = wearable_service
        self._config = config or {}
        self._storage_client = None
        logger.info("DeviceDataCollector initialized.")

    async def collect_and_store_data(
        self,
        user_id: UUID,
        target_date: date,
        preferred_source: DataSource  # <-- This is recognized from the imported DataSource
    ) -> Optional[StoredDeviceData]:
        """
        Fetches processed wearable data for a given day using WearableService,
        transforms it into StoredDeviceData format, and persists it.
        """
        logger.info(
            f"Collecting device data for user={user_id}, date={target_date}, source={preferred_source.name}"
        )

        if not self.wearable_service:
            logger.error("No WearableService instance available.")
            return None

        try:
            processed_data: Optional[ProcessedWearableData] = await self.wearable_service.get_processed_data_for_day(
                user_id=user_id,
                target_date=target_date,
                preferred_source=preferred_source,
            )
            if not processed_data:
                logger.warning("No processed data returned by WearableService.")
                return None

            storage_entry = StoredDeviceData(
                user_id=user_id,
                target_date=target_date,
                data_source=preferred_source.value,
            )

            if processed_data.sleep_analysis:
                sa = processed_data.sleep_analysis
                object.__setattr__(storage_entry, 'sleep_quality_score', sa.sleep_quality_score)
                if sa.actual_duration:
                    object.__setattr__(storage_entry, 'actual_sleep_duration_minutes', sa.actual_duration.total_seconds() / 60.0)
                if sa.sleep_deficit:
                    object.__setattr__(storage_entry, 'sleep_deficit_minutes', sa.sleep_deficit.total_seconds() / 60.0)

            object.__setattr__(storage_entry, 'resting_hr_avg_bpm', processed_data.resting_hr_avg_bpm)
            object.__setattr__(storage_entry, 'hrv_avg_rmssd_ms', processed_data.hrv_avg_rmssd_ms)

            if processed_data.activity_summary:
                act = processed_data.activity_summary
                object.__setattr__(storage_entry, 'steps', act.steps)
                object.__setattr__(storage_entry, 'active_minutes', act.active_minutes)
                object.__setattr__(storage_entry, 'calories_burned', act.calories_burned)

            if processed_data.raw_data_info:
                try:
                    raw_ref_str = json.dumps(processed_data.raw_data_info)
                    object.__setattr__(storage_entry, 'raw_data_reference', raw_ref_str)
                except TypeError:
                    logger.warning("Could not serialize raw_data_info to JSON.")
                    object.__setattr__(storage_entry, 'raw_data_reference', str(processed_data.raw_data_info))

            # --- Placeholder for Storage Logic ---
            storage_successful = True  # Simulate success for now
            if storage_successful:
                logger.info(f"Data prepared for storage (ID={storage_entry.record_id}) for user={user_id}.")
                return storage_entry
            else:
                logger.error(f"Failed to store device data for user {user_id}, date {target_date}.")
                return None

        except Exception as e:
            logger.exception(f"Error in collect_and_store_data: {e}")
            return None


# --- Example usage (for demonstration) ---
async def run_example():
    """Runs a simple demonstration of DeviceDataCollector usage with mocks."""
    import asyncio
    from uuid import uuid4
    from datetime import timedelta

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Running DeviceDataCollector Example ---")

    # --- Mock Dependencies ---
    # 1. Mock DeviceAdapter (from the adapter module)
    from src.adapters.device_adapter import MockDeviceDataAdapter
    mock_device_adapter = MockDeviceDataAdapter()

    # 2. Create a proper SleepCalculator mock.
    # Import SleepCalculator from WearableService module.
    from src.services.wearables import SleepCalculator

    # Define a dummy SleepMetrics class to be returned by SleepCalculator methods.
    @dataclass
    class MockSleepMetrics:
        sleep_quality_score: Optional[float] = 80.0
        actual_duration: Optional[timedelta] = timedelta(hours=7, minutes=30)
        sleep_deficit: Optional[timedelta] = timedelta(minutes=30)
        ideal_duration: timedelta = timedelta(hours=8)
        ideal_bedtime: time = time(23, 0)
        ideal_wake_time: time = time(7, 0)
        actual_bedtime: Optional[time] = time(23, 15)
        actual_wake_time: Optional[time] = time(6, 45)

    # Create a mock SleepCalculator as a subclass of the real SleepCalculator.
    class MockSleepCalculator(SleepCalculator):
        def calculate_sleep_window(self, *args, **kwargs) -> MockSleepMetrics:
            return MockSleepMetrics()

        def analyze_sleep_quality(self, recommended, sleep_start, sleep_end, **kwargs) -> MockSleepMetrics:
            actual_duration = sleep_end - sleep_start
            deficit = recommended.ideal_duration - actual_duration
            return MockSleepMetrics(
                sleep_quality_score=random.uniform(60, 95),
                actual_duration=actual_duration,
                sleep_deficit=deficit,
                actual_bedtime=sleep_start.astimezone(None).time(),
                actual_wake_time=sleep_end.astimezone(None).time(),
                ideal_duration=recommended.ideal_duration,
                ideal_bedtime=recommended.ideal_bedtime,
                ideal_wake_time=recommended.ideal_wake_time,
            )

    # Instantiate the mock sleep calculator
    mock_sleep_calculator = MockSleepCalculator()

    # 3. Create WearableService with mocks
    wearable_service = WearableService(
        device_adapter=mock_device_adapter,
        sleep_calculator=mock_sleep_calculator
    )
    # --- End Mock Dependencies ---

    # Initialize the collector with the mocked service
    collector = DeviceDataCollector(wearable_service=wearable_service)
    test_user_id = uuid4()
    test_date = date.today() - timedelta(days=1)

    print(f"\n--- Collecting Mock Device Data for User {test_user_id} on {test_date} ---")
    stored_data = await collector.collect_and_store_data(
        user_id=test_user_id,
        target_date=test_date,
        preferred_source=DataSource.MOCK
    )

    if stored_data:
        from dataclasses import asdict
        print("\n--- Collected StoredDeviceData ---")
        print(json.dumps(asdict(stored_data), indent=2, default=str))
    else:
        print("\nFailed to collect or store device data.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_example())
