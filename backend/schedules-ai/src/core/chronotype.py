# === File: scheduler-core/src/core/chronotype.py ===

"""
Chronotype Analysis and Management Module.

Handles the determination, representation, and application of user chronotypes
within the scheduling system. This includes:
- Defining chronotype categories (Enum).
- Representing a user's chronotype profile (Dataclass).
- Determining chronotype from questionnaires (e.g., MEQ) or sleep data.
- Suggesting optimal time blocks based on the profile.
- Updating the profile based on new data.
"""

import logging
import statistics
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class Chronotype(Enum):
    """
    User chronotype classification based on natural inclination for activity/sleep.
    """
    EARLY_BIRD = "early_bird"
    NIGHT_OWL = "night_owl"
    INTERMEDIATE = "intermediate"
    FLEXIBLE = "flexible"
    UNKNOWN = "unknown"


DEFAULT_MEQ_RANGES: Dict[Tuple[int, int], Chronotype] = {
    (16, 30): Chronotype.NIGHT_OWL,
    (31, 41): Chronotype.NIGHT_OWL,
    (42, 58): Chronotype.INTERMEDIATE,
    (59, 69): Chronotype.EARLY_BIRD,
    (70, 86): Chronotype.EARLY_BIRD,
}

DEFAULT_PRODUCTIVE_WINDOWS: Dict[Chronotype, List[Tuple[time, time]]] = {
    Chronotype.EARLY_BIRD: [(time(7, 0), time(12, 0)), (time(15, 0), time(17, 0))],
    Chronotype.NIGHT_OWL: [(time(10, 0), time(13, 0)), (time(17, 0), time(22, 0))],
    Chronotype.INTERMEDIATE: [(time(9, 0), time(12, 0)), (time(14, 0), time(18, 0))],
    Chronotype.FLEXIBLE: [(time(9, 0), time(13, 0)), (time(15, 0), time(19, 0))],
    Chronotype.UNKNOWN: [(time(9, 0), time(12, 0)), (time(14, 0), time(17, 0))],
}

DEFAULT_OPTIMAL_EXERCISE_TIMES: Dict[Chronotype, time] = {
    Chronotype.EARLY_BIRD: time(7, 0),
    Chronotype.NIGHT_OWL: time(18, 0),
    Chronotype.INTERMEDIATE: time(17, 0),
    Chronotype.FLEXIBLE: time(16, 0),
    Chronotype.UNKNOWN: time(17, 0),
}

DEFAULT_CHRONOTYPE_CONFIG: Dict[str, Any] = {
    "meq_ranges": DEFAULT_MEQ_RANGES,
    "default_productive_windows": DEFAULT_PRODUCTIVE_WINDOWS,
    "optimal_exercise_times": DEFAULT_OPTIMAL_EXERCISE_TIMES,
    "sleep_data_min_records": 7,
    "midsleep_threshold_early": 3.5,
    "midsleep_threshold_late": 5.5,
    "confidence_variance_scale": 4.0,
    "min_focus_block_break_minutes": 15,
    "update_profile_confidence_threshold": 0.6,
    "chronotype_sleep_time_adjustments": {
        Chronotype.EARLY_BIRD: -1.5,
        Chronotype.NIGHT_OWL: 1.5,
        Chronotype.INTERMEDIATE: 0.0,
        Chronotype.FLEXIBLE: 0.0,
        Chronotype.UNKNOWN: 0.0,
    },
}


def _deep_merge_dicts(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merges 'update' dict into 'base' dict."""
    merged = base.copy()
    for key, value in update.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


@dataclass
class ChronotypeProfile:
    """
    Represents a user's chronotype profile, including determined type,
    preferences, and consistency metrics.
    """

    user_id: UUID
    primary_chronotype: Chronotype = Chronotype.UNKNOWN
    chronotype_strength: float = field(default=0.5)
    consistency_score: float = field(default=1.0)
    natural_bedtime: Optional[time] = None
    natural_wake_time: Optional[time] = None
    preferred_productive_hours: List[Tuple[time, time]] = field(default_factory=list)
    preferred_exercise_time: Optional[time] = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_of_determination: Optional[str] = None

    def __post_init__(self) -> None:
        self.chronotype_strength = max(0.0, min(1.0, self.chronotype_strength))
        self.consistency_score = max(0.0, min(1.0, self.consistency_score))
        if not isinstance(self.preferred_productive_hours, list):
            self.preferred_productive_hours = list(self.preferred_productive_hours)

    def __str__(self) -> str:
        prod_hours_str = ", ".join(
            [
                f"{s.strftime('%H:%M')}-{e.strftime('%H:%M')}"
                for s, e in self.preferred_productive_hours
            ]
        )
        return (
            f"ChronotypeProfile(User: {self.user_id}, Type: {self.primary_chronotype.value}, "
            f"Strength: {self.chronotype_strength:.2f}, Consistency: {self.consistency_score:.2f}, "
            f"Productive: [{prod_hours_str}], Source: {self.source_of_determination}, "
            f"Updated: {self.last_updated.isoformat()})"
        )


class ChronotypeAnalyzer:
    """
    Analyzes user data (MEQ scores, sleep patterns) to determine and manage
    chronotype profiles using configurable parameters.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        merged_config = _deep_merge_dicts(deepcopy(DEFAULT_CHRONOTYPE_CONFIG), config if config else {})
        self._config = merged_config
        self._meq_ranges: Dict[Tuple[int, int], Chronotype] = self._config["meq_ranges"]
        self._default_productive_windows: Dict[Chronotype, List[Tuple[time, time]]] = self._config["default_productive_windows"]
        self._optimal_exercise_times: Dict[Chronotype, time] = self._config["optimal_exercise_times"]
        self._sleep_data_min_records: int = self._config["sleep_data_min_records"]
        self._midsleep_threshold_early: float = self._config["midsleep_threshold_early"]
        self._midsleep_threshold_late: float = self._config["midsleep_threshold_late"]
        self._confidence_variance_scale: float = self._config["confidence_variance_scale"]
        self._min_focus_block_break_minutes: int = self._config["min_focus_block_break_minutes"]
        self._update_profile_confidence_threshold: float = self._config["update_profile_confidence_threshold"]
        self._chronotype_sleep_time_adjustments: Dict[Chronotype, float] = self._config["chronotype_sleep_time_adjustments"]

        if not (0.1 <= self._update_profile_confidence_threshold <= 1.0):
            logger.warning(
                f"Configured 'update_profile_confidence_threshold' ({self._update_profile_confidence_threshold}) "
                f"is outside the typical range [0.1, 1.0]."
            )
        if self._sleep_data_min_records < 3:
            logger.warning(
                f"Configured 'sleep_data_min_records' ({self._sleep_data_min_records}) is very low, "
                f"results may be unreliable."
            )
        for chrono, adj in self._chronotype_sleep_time_adjustments.items():
            if not (-3.0 <= adj <= 3.0):
                logger.warning(
                    f"Configured 'chronotype_sleep_time_adjustments' for {chrono.value} ({adj}h) "
                    f"is outside the typical range [-3.0, 3.0]."
                )

        logger.info("ChronotypeAnalyzer initialized.")
        logger.debug(f"Using effective configuration: {self._config}")

    def determine_chronotype_from_meq(self, meq_score: int) -> Chronotype:
        """
        Determines chronotype based on a Morningness-Eveningness Questionnaire score.
        """
        all_scores = [s for r in self._meq_ranges.keys() for s in r]
        if not all_scores:
            raise ValueError("MEQ ranges configuration is empty.")
        valid_range_min = min(all_scores)
        valid_range_max = max(all_scores)

        if not (valid_range_min <= meq_score <= valid_range_max):
            msg = (
                f"Invalid MEQ score: {meq_score}. Valid range based on config is "
                f"{valid_range_min}-{valid_range_max}."
            )
            logger.error(msg)
            raise ValueError(msg)

        for score_range, chronotype in self._meq_ranges.items():
            min_score, max_score = score_range
            if min_score <= meq_score <= max_score:
                logger.debug(f"MEQ score {meq_score} maps to chronotype: {chronotype.value}")
                return chronotype

        logger.warning(
            f"Could not map MEQ score {meq_score} to a chronotype using configured ranges. "
            f"Defaulting to {Chronotype.INTERMEDIATE.value}."
        )
        return Chronotype.INTERMEDIATE

    def determine_chronotype_from_sleep_data(
        self,
        sleep_records: List[Tuple[datetime, datetime]],
        user_timezone: tzinfo,
    ) -> Optional[Tuple[Chronotype, float]]:
        """
        Determines chronotype and confidence based on mid-sleep time from sleep data.
        """
        if not sleep_records or len(sleep_records) < self._sleep_data_min_records:
            logger.warning(
                f"Insufficient sleep records: {len(sleep_records)} provided, "
                f"need at least {self._sleep_data_min_records}."
            )
            return None

        mid_sleep_times_hours: List[float] = []
        valid_records_count = 0

        for i, (sleep_start, sleep_end) in enumerate(sleep_records):
            if not isinstance(sleep_start, datetime) or not isinstance(sleep_end, datetime):
                logger.warning(
                    f"Skipping record {i+1}: Invalid type(s) - "
                    f"Start: {type(sleep_start)}, End: {type(sleep_end)}"
                )
                continue
            if sleep_end <= sleep_start:
                logger.warning(
                    f"Skipping record {i+1}: End time ({sleep_end}) is not after "
                    f"start time ({sleep_start})."
                )
                continue
            if sleep_start.tzinfo is None or sleep_end.tzinfo is None:
                logger.warning(
                    f"Skipping record {i+1}: Datetime(s) are timezone-naive. "
                    f"Start: {sleep_start}, End: {sleep_end}"
                )
                continue

            duration = sleep_end - sleep_start
            if not (timedelta(hours=3) <= duration <= timedelta(hours=14)):
                logger.warning(
                    f"Skipping record {i+1}: Unusual duration ({duration}). "
                    f"Start: {sleep_start}, End: {sleep_end}"
                )
                continue

            mid_sleep_dt_utc = sleep_start + duration / 2
            try:
                mid_sleep_dt_local = mid_sleep_dt_utc.astimezone(user_timezone)
            except Exception as e:
                logger.warning(
                    f"Skipping record {i+1}: Could not convert mid-sleep time {mid_sleep_dt_utc} "
                    f"to user timezone {user_timezone}. Error: {e}"
                )
                continue

            mid_sleep_hour = (
                mid_sleep_dt_local.hour
                + mid_sleep_dt_local.minute / 60.0
                + mid_sleep_dt_local.second / 3600.0
            )
            mid_sleep_times_hours.append(mid_sleep_hour)
            valid_records_count += 1

        if valid_records_count < self._sleep_data_min_records:
            logger.warning(
                f"Insufficient valid sleep records after filtering: {valid_records_count} found, "
                f"need at least {self._sleep_data_min_records}."
            )
            return None

        avg_mid_sleep_hour = statistics.mean(mid_sleep_times_hours)
        stdev_mid_sleep_hour = statistics.stdev(mid_sleep_times_hours) if valid_records_count > 1 else 0.0

        if avg_mid_sleep_hour <= self._midsleep_threshold_early:
            chronotype = Chronotype.EARLY_BIRD
        elif avg_mid_sleep_hour >= self._midsleep_threshold_late:
            chronotype = Chronotype.NIGHT_OWL
        else:
            chronotype = Chronotype.INTERMEDIATE

        normalized_stdev = stdev_mid_sleep_hour / max(0.1, self._confidence_variance_scale)
        confidence = max(0.0, 1.0 - normalized_stdev)

        logger.info(
            f"Determined chronotype {chronotype.value} with confidence {confidence:.3f} "
            f"from {valid_records_count} valid sleep records (Avg Mid-Sleep: {avg_mid_sleep_hour:.2f}h, "
            f"StDev: {stdev_mid_sleep_hour:.2f}h)"
        )
        return chronotype, confidence

    def create_chronotype_profile(
        self,
        user_id: UUID,
        chronotype: Chronotype,
        source: str,
        natural_bedtime: Optional[time] = None,
        natural_wake_time: Optional[time] = None,
        chronotype_strength: float = 0.5,
        consistency_score: float = 1.0,
    ) -> ChronotypeProfile:
        """
        Creates a new ChronotypeProfile for a user.
        """
        productive_windows = self._default_productive_windows.get(chronotype, [])
        exercise_time = self._optimal_exercise_times.get(chronotype)

        if natural_bedtime is None or natural_wake_time is None:
            base_wake = time(7, 30)
            adjustment_hours = self._chronotype_sleep_time_adjustments.get(chronotype, 0.0)
            base_dt = datetime.combine(date.today(), base_wake)
            inferred_wake_dt = base_dt + timedelta(hours=adjustment_hours)
            inferred_bed_dt = inferred_wake_dt - timedelta(hours=8)

            natural_wake_time = inferred_wake_dt.time()
            natural_bedtime = inferred_bed_dt.time()
            logger.debug(
                f"Inferred natural sleep times for {chronotype.value}: "
                f"Bed={natural_bedtime.strftime('%H:%M')}, Wake={natural_wake_time.strftime('%H:%M')}"
            )

        profile = ChronotypeProfile(
            user_id=user_id,
            primary_chronotype=chronotype,
            natural_bedtime=natural_bedtime,
            natural_wake_time=natural_wake_time,
            preferred_productive_hours=productive_windows,
            preferred_exercise_time=exercise_time,
            chronotype_strength=chronotype_strength,
            consistency_score=consistency_score,
            source_of_determination=source,
        )

        logger.info(f"Created new chronotype profile for user {user_id}: {profile}")
        return profile

    def get_optimal_focus_blocks(
        self,
        profile: ChronotypeProfile,
        target_date: date,
        block_duration: timedelta = timedelta(minutes=90),
        min_blocks: int = 2,
        max_blocks: int = 4,
    ) -> List[Tuple[datetime, datetime]]:
        """
        Generates suggested optimal focus time blocks for a given date based
        on the user's chronotype profile's preferred productive hours.
        """
        if not isinstance(profile, ChronotypeProfile):
            raise ValueError("Invalid ChronotypeProfile object provided.")
        if not isinstance(target_date, date):
            raise ValueError("Invalid target_date provided. Expected datetime.date.")
        if block_duration.total_seconds() <= 0:
            raise ValueError("Block duration must be positive.")

        min_break_td = timedelta(minutes=self._min_focus_block_break_minutes)
        preferred_hours = profile.preferred_productive_hours

        if not preferred_hours:
            logger.warning(
                f"No preferred productive hours found in profile for user {profile.user_id}. "
                f"Cannot generate focus blocks."
            )
            return []

        focus_blocks: List[Tuple[datetime, datetime]] = []
        preferred_ranges_today: List[Tuple[datetime, datetime]] = []
        for start_t, end_t in preferred_hours:
            start_dt = datetime.combine(target_date, start_t, tzinfo=timezone.utc)
            end_dt = datetime.combine(target_date, end_t, tzinfo=timezone.utc)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
            preferred_ranges_today.append((start_dt, end_dt))

        preferred_ranges_today.sort()

        for range_start, range_end in preferred_ranges_today:
            current_block_start = range_start
            while len(focus_blocks) < max_blocks:
                current_block_end = current_block_start + block_duration
                if current_block_end <= range_end:
                    focus_blocks.append((current_block_start, current_block_end))
                    logger.debug(
                        f"Added focus block: "
                        f"{current_block_start.strftime('%H:%M')} - {current_block_end.strftime('%H:%M')} UTC"
                    )
                    current_block_start = current_block_end + min_break_td
                else:
                    break
            if len(focus_blocks) >= max_blocks:
                break

        if len(focus_blocks) < min_blocks:
            logger.info(
                f"Generated {len(focus_blocks)} blocks, less than minimum ({min_blocks}). "
                f"No fallback implemented."
            )

        focus_blocks.sort()
        logger.info(
            f"Generated {len(focus_blocks)} focus blocks for user {profile.user_id} "
            f"on {target_date} (Duration: {block_duration})."
        )
        return focus_blocks[:max_blocks]

    def adjust_schedule_for_chronotype(
        self,
        schedule_items: List[Dict[str, Any]],
        profile: ChronotypeProfile,
    ) -> List[Dict[str, Any]]:
        """
        Adjusts task timing or priorities in a schedule based on chronotype.
        (Placeholder - real logic should integrate with a constraint solver, etc.)
        """
        logger.warning(
            f"Placeholder function 'adjust_schedule_for_chronotype' called for "
            f"user {profile.user_id} ({profile.primary_chronotype.value}). "
            f"Actual adjustment logic not yet implemented."
        )
        return schedule_items

    def update_chronotype_profile(
        self,
        profile: ChronotypeProfile,
        new_sleep_records: List[Tuple[datetime, datetime]],
        user_timezone: tzinfo,  # <--- ADDED THIS PARAMETER
    ) -> ChronotypeProfile:
        """
        Updates an existing chronotype profile based on new sleep data.

        Recalculates chronotype, confidence (strength), and consistency score
        using the new data. Updates the profile only if the confidence from
        the new data meets a configured threshold.

        Args:
            profile (ChronotypeProfile): The existing ChronotypeProfile object to update.
            new_sleep_records (List[Tuple[datetime, datetime]]): A list of new sleep
                records (start_time, end_time) as timezone-aware datetimes (UTC or otherwise).
            user_timezone (tzinfo): The user's local timezone, required for
                recalculating chronotype from sleep data.

        Returns:
            ChronotypeProfile: The updated profile, or the original profile if the
                               update criteria are not met or if an error occurs.
        """
        if not isinstance(profile, ChronotypeProfile):
            logger.error("Invalid profile object provided for update.")
            return profile
        if not new_sleep_records:
            logger.debug("No new sleep records provided for profile update. Returning original profile.")
            return profile

        logger.info(
            f"Attempting to update chronotype profile for user {profile.user_id} with "
            f"{len(new_sleep_records)} new sleep records."
        )

        if not isinstance(user_timezone, tzinfo):
            logger.error(
                f"Invalid user_timezone provided for profile update: {type(user_timezone)}. "
                f"Profile not updated."
            )
            return profile

        try:
            analysis_result = self.determine_chronotype_from_sleep_data(new_sleep_records, user_timezone)
            if analysis_result is None:
                logger.info(
                    "Could not determine chronotype from new sleep records "
                    "(e.g., insufficient data). Profile not updated."
                )
                return profile

            new_chronotype, confidence = analysis_result
            if confidence < self._update_profile_confidence_threshold:
                logger.info(
                    f"Confidence ({confidence:.3f}) from new sleep data is below threshold "
                    f"({self._update_profile_confidence_threshold}). Profile not updated."
                )
                return profile

            profile.primary_chronotype = new_chronotype
            profile.chronotype_strength = confidence
            profile.consistency_score = profile.consistency_score * 0.7 + confidence * 0.3
            profile.consistency_score = max(0.0, min(1.0, profile.consistency_score))
            profile.source_of_determination = "sleep_data_update"
            profile.last_updated = datetime.now(timezone.utc)

            update_prefs = True
            if update_prefs:
                profile.preferred_productive_hours = self._default_productive_windows.get(
                    new_chronotype,
                    self._default_productive_windows[Chronotype.UNKNOWN],
                )
                profile.preferred_exercise_time = self._optimal_exercise_times.get(
                    new_chronotype,
                    self._optimal_exercise_times[Chronotype.UNKNOWN],
                )
                logger.debug(
                    "Updated preferred productive hours and exercise time based on new chronotype."
                )

            logger.info(
                f"Successfully updated chronotype profile for user {profile.user_id} to "
                f"{new_chronotype.value} (Strength: {confidence:.3f}, "
                f"Consistency: {profile.consistency_score:.3f})."
            )
            return profile

        except Exception as e:
            logger.exception(f"Error updating chronotype profile for user {profile.user_id}")
            return profile


# --- Example Usage ---
async def run_example():
    """
    Demonstrates how to use ChronotypeAnalyzer with MEQ scores, sleep data,
    and profile creation/updating.
    """
    import asyncio
    from uuid import uuid4

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("--- Running ChronotypeAnalyzer Example ---")

    analyzer = ChronotypeAnalyzer()

    # Example 1: Determine from MEQ
    print("\n--- MEQ Determination ---")
    try:
        meq_score = 65  # Moderate morning
        chrono_meq = analyzer.determine_chronotype_from_meq(meq_score)
        print(f"MEQ Score {meq_score} -> Chronotype: {chrono_meq.value}")
    except ValueError as e:
        print(f"Error for MEQ score {meq_score}: {e}")

    # Example 2: Sleep Data
    print("\n--- Sleep Data Determination ---")
    try:
        import pytz
        user_tz = pytz.timezone("Europe/Warsaw")
    except ImportError:
        user_tz = timezone(timedelta(hours=2))
        print("Note: pytz not installed, using fixed offset timezone for example.")

    sleep_data_early = [
        (datetime(2024, 1, 10, 22, 5, tzinfo=timezone.utc), datetime(2024, 1, 11, 5, 35, tzinfo=timezone.utc)),
        (datetime(2024, 1, 11, 22, 15, tzinfo=timezone.utc), datetime(2024, 1, 12, 5, 45, tzinfo=timezone.utc)),
        (datetime(2024, 1, 12, 21, 55, tzinfo=timezone.utc), datetime(2024, 1, 13, 5, 25, tzinfo=timezone.utc)),
        (datetime(2024, 1, 13, 22, 10, tzinfo=timezone.utc), datetime(2024, 1, 14, 5, 40, tzinfo=timezone.utc)),
        (datetime(2024, 1, 14, 22, 0, tzinfo=timezone.utc), datetime(2024, 1, 15, 5, 30, tzinfo=timezone.utc)),
        (datetime(2024, 1, 15, 21, 50, tzinfo=timezone.utc), datetime(2024, 1, 16, 5, 20, tzinfo=timezone.utc)),
        (datetime(2024, 1, 16, 22, 5, tzinfo=timezone.utc), datetime(2024, 1, 17, 5, 35, tzinfo=timezone.utc)),
    ]
    result_early = analyzer.determine_chronotype_from_sleep_data(sleep_data_early, user_tz)
    if result_early:
        print(f"Early Bird Data -> Chronotype: {result_early[0].value}, Confidence: {result_early[1]:.3f}")

    # Example 3: Profile Creation & Update
    print("\n--- Profile Creation & Update ---")
    user_uuid = uuid4()
    initial_profile = analyzer.create_chronotype_profile(
        user_id=user_uuid,
        chronotype=chrono_meq,
        source="meq_initial",
        chronotype_strength=0.65,
        consistency_score=0.8,
    )
    print(f"Initial Profile: {initial_profile}")

    updated_profile = analyzer.update_chronotype_profile(initial_profile, sleep_data_early, user_tz)
    print(f"Updated Profile: {updated_profile}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_example())
