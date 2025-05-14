# === File: scheduler-core/src/services/wearables.py ===

"""
Wearable Data Processing Service.

Fetches data using a DeviceDataAdapter, processes it into meaningful metrics
(e.g., sleep quality analysis, physiological averages during sleep), and provides
a consolidated view for use in scheduling and analytics.
"""

import logging
import statistics
import asyncio # Added import for asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone, time
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

# Application-specific imports (absolute paths)
try:
    from src.adapters.device_adapter import (
        ActivityDataSummary, # Renamed from ActivityData
        DataSource,
        DeviceAdapterProtocol, # Use the protocol for dependency
        HeartRateDataPoint,
        HrvDataPoint,
        SleepDataRecord,
    )
    from src.core.sleep import SleepCalculator, SleepMetrics, Chronotype
    # Chronotype might not be directly needed here unless used in processing logic
    # from src.core.chronotype import Chronotype
    CORE_IMPORTS_OK = True
except ImportError as e:
    logging.getLogger(__name__).error(f"Failed to import core components for WearableService: {e}", exc_info=True)
    CORE_IMPORTS_OK = False
    # Define placeholders if needed
    class DeviceAdapterProtocol: pass # type: ignore
    class SleepCalculator: pass # type: ignore
    class SleepMetrics: pass # type: ignore
    class ActivityDataSummary: pass # type: ignore
    class SleepDataRecord: pass # type: ignore
    class HeartRateDataPoint: pass # type: ignore
    class HrvDataPoint: pass # type: ignore
    from enum import Enum # type: ignore
    class DataSource(Enum): MOCK = "mock" # type: ignore


logger = logging.getLogger(__name__)


# --- Data Structures ---

def format_timedelta(td: timedelta) -> str:
    """Formats a timedelta into a string 'HH:MM'."""
    if td is None:
        return "N/A"
    total_minutes = int(td.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


@dataclass(frozen=True) # Use frozen for immutable results
class ProcessedWearableData:
    """
    Consolidated processed wearable data for a specific target date.

    Attributes:
        user_id: The user to whom this data belongs.
        target_date: The primary date this data pertains to.
        sleep_analysis: Detailed sleep analysis results, including quality score,
                        actual times, and deficit (if calculated). Represents the
                        sleep period *ending* on the morning of target_date.
        activity_summary: Summary of activity metrics for the target_date.
        resting_hr_avg_bpm: Average heart rate during the primary sleep period (BPM).
        hrv_avg_rmssd_ms: Average Heart Rate Variability (RMSSD) during the primary
                          sleep period (milliseconds).
        raw_data_info: Optional dictionary containing references or metadata about
                       the source data used for processing.
    """
    user_id: UUID
    target_date: date
    sleep_analysis: Optional[SleepMetrics] = None
    activity_summary: Optional[ActivityDataSummary] = None
    resting_hr_avg_bpm: Optional[float] = None
    hrv_avg_rmssd_ms: Optional[float] = None
    raw_data_info: Dict[str, Any] = field(default_factory=dict) # e.g., {"sleep_record_ids": [...]}


# --- Wearable Service Class ---

class WearableService:
    """
    Provides high-level methods to access processed wearable data.

    Orchestrates fetching data via a DeviceAdapter and analyzing it using
    components like SleepCalculator.
    """

    def __init__(
        self,
        device_adapter: DeviceAdapterProtocol, # Depend on the protocol
        sleep_calculator: SleepCalculator,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initializes the WearableService.

        Args:
            device_adapter (DeviceAdapterProtocol): Adapter instance to fetch data.
            sleep_calculator (SleepCalculator): Instance for sleep analysis functions.
            config (Optional[Dict[str, Any]]): Configuration dictionary, e.g.:
                {
                    "primary_sleep_end_window_start_hour": 0, # Default 00:00 UTC
                    "primary_sleep_end_window_end_hour": 14 # Default 14:00 UTC
                }

        Raises:
            ImportError: If essential core components failed to import.
            TypeError: If dependencies are not of the expected type.
        """
        if not CORE_IMPORTS_OK:
            raise ImportError("WearableService cannot be initialized due to missing core dependencies.")
        # Rely on static type checking and duck typing for the adapter protocol
        # if not isinstance(device_adapter, DeviceAdapterProtocol): # Removed runtime check
        #     logger.warning("device_adapter may not fully implement DeviceAdapterProtocol.")
        if not isinstance(sleep_calculator, SleepCalculator):
             raise TypeError("sleep_calculator must be an instance of SleepCalculator.")

        self.device_adapter = device_adapter
        self.sleep_calculator = sleep_calculator
        self._config = config or {}
        # Get configuration for sleep window or use defaults
        self._sleep_window_start_hour: int = self._config.get("primary_sleep_end_window_start_hour", 0)
        self._sleep_window_end_hour: int = self._config.get("primary_sleep_end_window_end_hour", 14)

        logger.info(
            f"WearableService initialized. Primary sleep window: "
            f"{self._sleep_window_start_hour:02d}:00 - {self._sleep_window_end_hour:02d}:00 UTC"
        )

    async def get_processed_data_for_day(
        self,
        user_id: UUID,
        target_date: date,
        preferred_source: DataSource = DataSource.MOCK,
        recommended_sleep: Optional[SleepMetrics] = None, # Needed for quality analysis
    ) -> ProcessedWearableData:
        """
        Fetches and processes wearable data for a specific user and date asynchronously.

        Retrieves activity for the target date and sleep/physiological data for the
        night *leading into* the target date. Performs sleep quality analysis if
        recommended sleep metrics are provided.

        Args:
            user_id (UUID): The user's identifier.
            target_date (date): The date for which to process data (activity for this date,
                                sleep for the night ending on this date's morning).
            preferred_source (DataSource): The preferred wearable data source.
            recommended_sleep (Optional[SleepMetrics]): Recommended sleep metrics used
                                                        for sleep quality scoring.

        Returns:
            ProcessedWearableData: An object containing the processed results.
                                   Fields may be None if data fetching or processing failed.
        """
        logger.info(
            f"Processing wearable data for user {user_id} on {target_date} "
            f"from preferred source: {preferred_source.name}"
        )

        # Initialize result object
        processed_data = ProcessedWearableData(user_id=user_id, target_date=target_date)
        raw_info: Dict[str, Any] = {}  # Aby przechować referencje do oryginalnych danych

        # --- 1. Fetch Activity Summary for the target date ---
        try:
            activity = await self.device_adapter.get_activity_summary(
                user_id, target_date, preferred_source
            )
            if activity:
                 # Use object.__setattr__ because ProcessedWearableData is frozen
                 object.__setattr__(processed_data, 'activity_summary', activity)
                 if activity.source_record_id: raw_info["activity_record_id"] = activity.source_record_id
                 logger.debug(f"Fetched activity summary: Steps={activity.steps}")
            else:
                 logger.info("No activity summary found for target date.")
        except Exception as e:
            logger.error(f"Failed to get activity summary: {e}", exc_info=True)

        # --- 2. Fetch Sleep Data for the night ending on target_date morning ---
        sleep_analysis_result: Optional[SleepMetrics] = None
        resting_hr: Optional[float] = None
        hrv_rmssd: Optional[float] = None
        primary_sleep_record: Optional[SleepDataRecord] = None

        sleep_query_start_date = target_date - timedelta(days=1)
        sleep_query_end_date = target_date # Fetch records ending on or before the end of target_date

        try:
            sleep_records = await self.device_adapter.get_sleep_data(
                user_id, sleep_query_start_date, sleep_query_end_date, preferred_source
            )

            # Identify the primary sleep session (e.g., longest one ending on target date morning)
            primary_sleep_record = self._find_primary_sleep_session(sleep_records, target_date)

            if primary_sleep_record:
                logger.info(f"Identified primary sleep session: {primary_sleep_record.start_time} - {primary_sleep_record.end_time}")
                if primary_sleep_record.source_record_id: raw_info["sleep_record_id"] = primary_sleep_record.source_record_id

                # --- 3. Fetch Physiological Data during Primary Sleep ---
                hr_data, hrv_data = await self._fetch_physiological_data(
                    user_id, primary_sleep_record, preferred_source
                )

                # --- 4. Calculate Averages ---
                resting_hr = self._calculate_average_metric(hr_data, 'bpm', "Resting HR")
                hrv_rmssd = self._calculate_average_metric(hrv_data, 'rmssd_ms', "HRV (RMSSD)")

                # --- 5. Analyze Sleep Quality ---
                if recommended_sleep:
                    try:
                        sleep_analysis_result = self.sleep_calculator.analyze_sleep_quality(
                            recommended=recommended_sleep,
                            sleep_start=primary_sleep_record.start_time,
                            sleep_end=primary_sleep_record.end_time,
                            heart_rate_data=[(p.timestamp, p.bpm) for p in hr_data],
                            hrv_data=[(p.timestamp, p.rmssd_ms) for p in hrv_data if p.rmssd_ms is not None]
                        )
                        logger.info(f"Sleep quality analysis complete. Score: {sleep_analysis_result.sleep_quality_score:.1f}")
                    except Exception as e:
                        logger.error(f"Failed during sleep quality analysis: {e}", exc_info=True)
                else:
                    logger.warning("Cannot analyze sleep quality: recommended_sleep metrics not provided.")
                    # Create partial metrics if analysis cannot be done
                    sleep_analysis_result = SleepMetrics(
                        ideal_duration=timedelta(0), ideal_bedtime=time(0,0), ideal_wake_time=time(0,0), # Dummy ideals
                        actual_duration=primary_sleep_record.duration,
                        actual_bedtime=primary_sleep_record.start_time.astimezone(None).time(),
                        actual_wake_time=primary_sleep_record.end_time.astimezone(None).time(),
                    )
            else:
                logger.info(f"No primary sleep session found ending on {target_date} morning.")

        except Exception as e:
            logger.error(f"Failed to get or process sleep/physiological data: {e}", exc_info=True)

        # --- 6. Assemble Final Result ---
        # Use object.__setattr__ because ProcessedWearableData is frozen
        if sleep_analysis_result: object.__setattr__(processed_data, 'sleep_analysis', sleep_analysis_result)
        if resting_hr: object.__setattr__(processed_data, 'resting_hr_avg_bpm', resting_hr)
        if hrv_rmssd: object.__setattr__(processed_data, 'hrv_avg_rmssd_ms', hrv_rmssd)
        if raw_info: object.__setattr__(processed_data, 'raw_data_info', raw_info)

        logger.info(f"Wearable data processing complete for user {user_id}, date {target_date}.")
        return processed_data


    def _find_primary_sleep_session(
        self, sleep_records: List[SleepDataRecord], target_date: date
    ) -> Optional[SleepDataRecord]:
        """
        Identifies the main sleep session ending on the morning of the target date.

        Selects the longest sleep record ending within the configured time window
        (e.g., 00:00 to 14:00 UTC) on the target date.
        """
        if not sleep_records:
            return None

        relevant_records = []
        # Use configured window start/end hours
        try:
            window_start_time = time(self._sleep_window_start_hour, 0)
            window_end_time = time(self._sleep_window_end_hour, 0)
        except ValueError:
             logger.error("Invalid sleep window hours configured. Using defaults 00:00-14:00.")
             window_start_time = time(0, 0)
             window_end_time = time(14, 0)

        target_start_dt = datetime.combine(target_date, window_start_time, tzinfo=timezone.utc)
        target_end_dt = datetime.combine(target_date, window_end_time, tzinfo=timezone.utc)

        for record in sleep_records:
             # Ensure record times are timezone-aware
             if record.start_time.tzinfo is None or record.end_time.tzinfo is None:
                  logger.warning(f"Skipping timezone-naive sleep record: {record.source_record_id}")
                  continue
             # Convert record times to UTC for consistent comparison
             record_end_utc = record.end_time.astimezone(timezone.utc)
             if target_start_dt <= record_end_utc <= target_end_dt:
                  relevant_records.append(record)

        if not relevant_records:
            return None

        # Simple logic: return the longest relevant sleep record
        primary_sleep = max(relevant_records, key=lambda r: r.duration)
        return primary_sleep


    async def _fetch_physiological_data(
        self, user_id: UUID, sleep_record: SleepDataRecord, source: DataSource
    ) -> Tuple[List[HeartRateDataPoint], List[HrvDataPoint]]:
        """Fetches HR and HRV data during the specified sleep record period."""
        hr_data: List[HeartRateDataPoint] = []
        hrv_data: List[HrvDataPoint] = []
        try:
            # Fetch data concurrently if adapter supports it, otherwise sequentially
            hr_task = asyncio.create_task(
                self.device_adapter.get_heart_rate_data(user_id, sleep_record.start_time, sleep_record.end_time, source)
            )
            hrv_task = asyncio.create_task(
                self.device_adapter.get_hrv_data(user_id, sleep_record.start_time, sleep_record.end_time, source)
            )
            hr_data = await hr_task
            hrv_data = await hrv_task
            logger.debug(f"Fetched {len(hr_data)} HR points and {len(hrv_data)} HRV points during sleep.")
        except Exception as e:
            logger.error(f"Failed to fetch physiological data during sleep: {e}", exc_info=True)
        return hr_data, hrv_data


    def _calculate_average_metric(
        self, data_points: List[Any], attribute_name: str, metric_name: str
    ) -> Optional[float]:
        """
        Calculates the average of a specific attribute from a list of data points.

        Filters out None or non-positive values before calculating the mean.
        """
        if not data_points:
            logger.debug(f"No data points provided for calculating average {metric_name}.")
            return None

        valid_values = [
            getattr(p, attribute_name) for p in data_points
            if hasattr(p, attribute_name) and getattr(p, attribute_name) is not None and getattr(p, attribute_name) > 0
        ]

        if not valid_values:
            logger.debug(f"No valid '{attribute_name}' values found for averaging {metric_name}.")
            return None

        try:
            average = statistics.mean(valid_values)
            logger.debug(f"Calculated average {metric_name}: {average:.2f} from {len(valid_values)} points.")
            return average
        except statistics.StatisticsError as e:
            logger.warning(f"Could not calculate mean {metric_name}: {e}")
            return None
        except Exception as e: # Catch any other unexpected errors during calculation
            logger.error(f"Unexpected error calculating average {metric_name}: {e}", exc_info=True)
            return None


# --- Example Usage ---
async def run_example():
    """Runs a simple example demonstrating WearableService usage."""
    # Ensure core imports are okay before proceeding
    if not CORE_IMPORTS_OK:
        print("Cannot run example: Core dependencies failed to import.")
        return

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Running WearableService Example ---")

    # Use Mock Adapter for example
    from src.adapters.device_adapter import MockDeviceDataAdapter
    mock_adapter = MockDeviceDataAdapter()
    mock_sleep_calculator = SleepCalculator()

    wearable_service = WearableService(
        device_adapter=mock_adapter,
        sleep_calculator=mock_sleep_calculator
    )

    test_user_id = uuid4()
    test_date = date.today() - timedelta(days=1) # Process data for yesterday

    # Get dummy recommended sleep for analysis
    recommended = mock_sleep_calculator.calculate_sleep_window(
        age=30, chronotype=Chronotype.INTERMEDIATE
    )

    print(f"\n--- Getting Processed Wearable Data for {test_date} ---")
    processed_wearables = await wearable_service.get_processed_data_for_day(
        user_id=test_user_id,
        target_date=test_date,
        preferred_source=DataSource.MOCK, # Use mock source
        recommended_sleep=recommended
    )

    print("\n--- Processed Data Result ---")
    if processed_wearables.activity_summary:
        act = processed_wearables.activity_summary
        print(f"Activity: Steps={act.steps}, ActiveMin={act.active_minutes}, Cal={act.calories_burned:.0f}")
    else: print("Activity: No data")

    if processed_wearables.sleep_analysis:
        sa = processed_wearables.sleep_analysis
        print(f"Sleep Analysis: Score={sa.sleep_quality_score:.1f}, Actual={format_timedelta(sa.actual_duration)}, Deficit={format_timedelta(sa.sleep_deficit)}")
        print(f"Avg Resting HR: {processed_wearables.resting_hr_avg_bpm:.1f} bpm" if processed_wearables.resting_hr_avg_bpm else "Avg Resting HR: N/A")
        print(f"Avg HRV (RMSSD): {processed_wearables.hrv_avg_rmssd_ms:.1f} ms" if processed_wearables.hrv_avg_rmssd_ms else "Avg HRV (RMSSD): N/A")
    else: print("Sleep Analysis: No data")
    print(f"Raw Data Info: {processed_wearables.raw_data_info}")


if __name__ == "__main__":
    import asyncio
    # Run the async example function
    asyncio.run(run_example())
