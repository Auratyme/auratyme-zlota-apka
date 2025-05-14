# === File: scheduler-core/src/core/sleep.py ===

"""
Sleep Analysis and Recommendation Module.

Provides functionality for calculating personalized sleep recommendations
(duration, timing) based on age, chronotype, and user preferences. It also
includes capabilities for analyzing actual sleep quality using metrics derived
from wearable data or other sources.
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# Application-specific imports (absolute paths)
try:
    # Import Chronotype if defined elsewhere, otherwise use local definition
    from src.core.chronotype import Chronotype
except ImportError:
    # Define locally if not available (e.g., for standalone use/testing)
    class Chronotype(Enum): # type: ignore
        EARLY_BIRD = "early_bird"
        NIGHT_OWL = "night_owl"
        INTERMEDIATE = "intermediate"
        UNKNOWN = "unknown"
    logging.getLogger(__name__).warning("Using local Chronotype Enum definition.")

try:
    from src.utils.time_utils import format_timedelta, time_to_total_minutes
    TIME_UTILS_AVAILABLE = True
except ImportError:
    logging.getLogger(__name__).warning("Could not import time helpers from src.utils. Defining locally.")
    TIME_UTILS_AVAILABLE = False
    def format_timedelta(delta: Optional[timedelta]) -> str:
        if delta is None: return "N/A"
        total_seconds = int(delta.total_seconds()); sign = "-" if total_seconds < 0 else ""; total_seconds = abs(total_seconds)
        h, rem = divmod(total_seconds, 3600); m, _ = divmod(rem, 60)
        return f"{sign}{h}h {m}m" if h > 0 else f"{sign}{m}m"
    def time_to_total_minutes(t: time) -> int: return t.hour * 60 + t.minute


logger = logging.getLogger(__name__)


# --- Default Configuration ---
# These values can be overridden by passing a config dict to SleepCalculator
DEFAULT_SLEEP_GUIDELINES: Dict[str, Tuple[float, float]] = {
    "teen": (8.0, 10.0),       # 13-18 years
    "young_adult": (7.0, 9.0), # 18-25 years
    "adult": (7.0, 9.0),       # 26-64 years
    "senior": (7.0, 8.0),      # 65+ years
}
DEFAULT_CHRONOTYPE_ADJUSTMENTS: Dict[Chronotype, float] = {
    Chronotype.EARLY_BIRD: -1.0, # Earlier wake/bed time (hours)
    Chronotype.NIGHT_OWL: 1.0,   # Later wake/bed time (hours)
    Chronotype.INTERMEDIATE: 0.0,
    Chronotype.UNKNOWN: 0.0,
}
DEFAULT_WAKE_TIMES: Dict[Chronotype, time] = {
    Chronotype.EARLY_BIRD: time(6, 30),
    Chronotype.INTERMEDIATE: time(7, 30),
    Chronotype.NIGHT_OWL: time(8, 30),
    Chronotype.UNKNOWN: time(7, 30),
}
DEFAULT_SLEEP_CONFIG: Dict[str, Any] = {
    "sleep_guidelines": DEFAULT_SLEEP_GUIDELINES,
    "chronotype_adjustments": DEFAULT_CHRONOTYPE_ADJUSTMENTS,
    "default_wake_times": DEFAULT_WAKE_TIMES,
    "sleep_cycle_duration_minutes": 90,
    "sleep_onset_minutes": 15, # Assumed time to fall asleep
    "max_sleep_need_adjustment_hours": 1.0, # Max duration adjustment from scale
    "max_chronotype_adjustment_hours": 1.5, # Max timing adjustment from scale
    # Quality Score Parameters
    "timing_tolerance_minutes": 30,
    "timing_penalty_range_minutes": 90,
    "duration_tolerance_minutes": 30,
    "duration_penalty_range_minutes": 90,
    "hr_target_min": 40, # Target minimum HR during sleep
    "hr_target_max": 60, # Target maximum HR during sleep (less common target)
    "hr_penalty_range_low": 10, # BPM below target_min for max penalty
    "hr_penalty_range_high": 20, # BPM above target_max for max penalty
    "hrv_target_avg_rmssd_ms": 50, # Example target average RMSSD
    "hrv_score_scale_factor": 1.0, # Factor to scale HRV contribution
    "quality_score_weights": {"duration": 0.4, "timing": 0.3, "physiological": 0.3},
    "physiological_sub_weights": {"hr": 0.5, "hrv": 0.5}, # Weights within physiological score
}


# --- Data Structures ---

@dataclass(frozen=True)
class SleepMetrics:
    """
    Container for sleep-related measurements and recommendations. Immutable.

    Attributes:
        ideal_duration: Recommended total sleep duration.
        ideal_bedtime: Recommended time to go to bed (local time).
        ideal_wake_time: Recommended time to wake up (local time).
        actual_duration: Actual total sleep duration from data (if available).
        actual_bedtime: Actual bedtime from data (local time, if available).
        actual_wake_time: Actual wake time from data (local time, if available).
        sleep_quality_score: Calculated overall sleep quality score (0-100, if calculated).
        sleep_deficit: Difference between ideal and actual duration (negative if slept longer).
    """
    # Recommended values
    ideal_duration: timedelta
    ideal_bedtime: time
    ideal_wake_time: time

    # Actual values from analysis (optional)
    actual_duration: Optional[timedelta] = None
    actual_bedtime: Optional[time] = None
    actual_wake_time: Optional[time] = None
    sleep_quality_score: Optional[float] = None

    # Derived metric
    sleep_deficit: Optional[timedelta] = field(init=False, default=None)

    def __post_init__(self):
        # Calculate deficit after initialization if actual duration is known
        if self.actual_duration is not None:
            # Use object.__setattr__ because the dataclass is frozen
            object.__setattr__(self, 'sleep_deficit', self.ideal_duration - self.actual_duration)

    def __str__(self) -> str:
        """String representation for easy logging."""
        rec_dur_str = format_timedelta(self.ideal_duration)
        act_dur_str = format_timedelta(self.actual_duration)
        deficit_str = format_timedelta(self.sleep_deficit)
        score_str = f"{self.sleep_quality_score:.1f}" if self.sleep_quality_score is not None else "N/A"
        bed_act = self.actual_bedtime.strftime('%H:%M') if self.actual_bedtime else 'N/A'
        wake_act = self.actual_wake_time.strftime('%H:%M') if self.actual_wake_time else 'N/A'

        return (
            f"SleepMetrics(Ideal: {self.ideal_bedtime.strftime('%H:%M')}-"
            f"{self.ideal_wake_time.strftime('%H:%M')} [{rec_dur_str}], "
            f"Actual: {bed_act}-{wake_act} [{act_dur_str}], "
            f"Deficit: {deficit_str}, Score: {score_str}/100)"
        )


# --- Sleep Calculator Class ---

class SleepCalculator:
    """
    Calculates optimal sleep schedules and analyzes sleep quality based on
    configurable parameters and provided user data.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initializes the SleepCalculator.

        Args:
            config (Optional[Dict[str, Any]]): A dictionary to override default
                configuration values specified in DEFAULT_SLEEP_CONFIG.
        """
        # Deep merge might be better for nested dicts like guidelines/weights
        self._config = DEFAULT_SLEEP_CONFIG.copy()
        if config:
            self._config.update(config) # Simple override for now

        # Store resolved config values for easier access and type checking
        self._sleep_guidelines: Dict[str, Tuple[float, float]] = self._config["sleep_guidelines"]
        self._chronotype_adjustments: Dict[Chronotype, float] = self._config["chronotype_adjustments"]
        self._default_wake_times: Dict[Chronotype, time] = self._config["default_wake_times"]
        self._sleep_cycle_duration_minutes: int = self._config["sleep_cycle_duration_minutes"]
        self._sleep_onset_minutes: int = self._config["sleep_onset_minutes"]
        self._max_sleep_need_adj: float = self._config["max_sleep_need_adjustment_hours"]
        self._max_chrono_adj: float = self._config["max_chronotype_adjustment_hours"]
        self._timing_tolerance: int = self._config["timing_tolerance_minutes"]
        self._timing_penalty_range: int = self._config["timing_penalty_range_minutes"]
        self._duration_tolerance: int = self._config["duration_tolerance_minutes"]
        self._duration_penalty_range: int = self._config["duration_penalty_range_minutes"]
        self._hr_target_min: int = self._config["hr_target_min"]
        self._hr_target_max: int = self._config["hr_target_max"]
        self._hr_penalty_low: int = self._config["hr_penalty_range_low"]
        self._hr_penalty_high: int = self._config["hr_penalty_range_high"]
        self._hrv_target: float = self._config["hrv_target_avg_rmssd_ms"]
        self._hrv_scale: float = self._config["hrv_score_scale_factor"]
        self._quality_weights: Dict[str, float] = self._config["quality_score_weights"]
        self._physio_weights: Dict[str, float] = self._config["physiological_sub_weights"]

        logger.info("SleepCalculator initialized.")
        logger.debug(f"Using effective sleep config: {self._config}")


    def get_recommended_sleep_duration(
        self,
        age: int,
        sleep_need_scale: Optional[float] = 50.0 # Default to average (50)
    ) -> timedelta:
        """
        Calculates recommended sleep duration based on age and preference scale.

        Args:
            age (int): User's age in years.
            sleep_need_scale (Optional[float]): User preference scale (0-100), where
                50 is average, <50 needs less, >50 needs more. Defaults to 50.

        Returns:
            timedelta: Recommended sleep duration.

        Raises:
            ValueError: If age is outside a reasonable range (e.g., 0-120).
        """
        if not (0 <= age <= 120):
            msg = f"Invalid age provided: {age}. Must be between 0 and 120."
            logger.error(msg)
            raise ValueError(msg)

        # Determine age category
        if age < 18: category = "teen"
        elif age < 26: category = "young_adult"
        elif age < 65: category = "adult"
        else: category = "senior"

        min_h, max_h = self._sleep_guidelines.get(category, (7.0, 9.0)) # Default fallback
        base_avg_h = (min_h + max_h) / 2.0

        # Adjust based on user preference scale
        adj_h = 0.0
        if sleep_need_scale is not None:
            if 0 <= sleep_need_scale <= 100:
                adj_factor = (sleep_need_scale - 50.0) / 50.0 # Scale to -1 to +1
                adj_h = adj_factor * self._max_sleep_need_adj
                logger.debug(f"Adjusting sleep duration by {adj_h:.2f}h based on scale {sleep_need_scale}")
            else:
                logger.warning(f"Invalid sleep_need_scale value: {sleep_need_scale}. Using base average.")

        final_h = base_avg_h + adj_h
        # Clamp duration within reasonable bounds (e.g., min_rec - 1h to max_rec + 1h, absolute 4-12h)
        reasonable_min = max(4.0, min_h - 1.0)
        reasonable_max = min(12.0, max_h + 1.0)
        final_h = max(reasonable_min, min(reasonable_max, final_h))

        logger.debug(f"Recommended sleep for age {age} ({category}), scale {sleep_need_scale}: {final_h:.2f} hours")
        return timedelta(hours=final_h)


    def calculate_sleep_window(
        self,
        age: int,
        chronotype: Chronotype,
        target_wake_time: Optional[time] = None,
        sleep_need_scale: Optional[float] = 50.0,
        chronotype_scale: Optional[float] = 50.0, # 0-100, <50 early, >50 late
    ) -> SleepMetrics:
        """
        Calculates an ideal sleep window (bedtime, wake time, duration).

        Determines duration based on age/preference, then adjusts timing based
        on chronotype preference scale or category, relative to a target wake time
        (or a default wake time if none is provided).

        Args:
            age (int): User's age in years.
            chronotype (Chronotype): User's determined chronotype category.
            target_wake_time (Optional[time]): Preferred wake time. If None, defaults
                                               based on chronotype from config.
            sleep_need_scale (Optional[float]): User preference scale (0-100) for duration.
            chronotype_scale (Optional[float]): User preference scale (0-100) for timing.

        Returns:
            SleepMetrics: Object containing the recommended sleep duration, bedtime, and wake time.
        """
        # 1. Get Recommended Duration
        sleep_duration = self.get_recommended_sleep_duration(age, sleep_need_scale)

        # 2. Determine Target Wake Time
        if target_wake_time is None:
            target_wake_time = self._default_wake_times.get(chronotype, time(7, 30))
            logger.debug(f"Using default wake time {target_wake_time.strftime('%H:%M')} for {chronotype.value}")
        if not isinstance(target_wake_time, time): # Basic type check
             raise TypeError("target_wake_time must be a datetime.time object or None.")

        # 3. Calculate Timing Adjustment
        timing_adj_h = 0.0
        if chronotype_scale is not None and 0 <= chronotype_scale <= 100:
            adj_factor = (chronotype_scale - 50.0) / 50.0 # Scale to -1 to +1
            timing_adj_h = adj_factor * self._max_chrono_adj
            logger.debug(f"Adjusting timing by {timing_adj_h:.2f}h based on scale {chronotype_scale}")
        else:
            timing_adj_h = self._chronotype_adjustments.get(chronotype, 0.0)
            logger.debug(f"Using category timing adjustment: {timing_adj_h:.1f}h for {chronotype.value}")

        # 4. Calculate Final Window
        # Use a reference date for datetime arithmetic, handle potential day changes
        ref_date = date.today() # Arbitrary date for calculation
        target_wake_dt = datetime.combine(ref_date, target_wake_time)
        # If target wake time is very early (e.g. < 4 AM), assume it's the next calendar day relative to bedtime
        if target_wake_time < time(4, 0):
             target_wake_dt += timedelta(days=1)

        adjusted_wake_dt = target_wake_dt + timedelta(hours=timing_adj_h)
        final_wake_time = adjusted_wake_dt.time()

        # Calculate ideal bedtime based on adjusted wake time and duration
        bedtime_dt = adjusted_wake_dt - sleep_duration
        final_bedtime = bedtime_dt.time()

        logger.info(
            f"Calculated sleep window: Bedtime={final_bedtime.strftime('%H:%M')}, "
            f"Wake={final_wake_time.strftime('%H:%M')}, Duration={format_timedelta(sleep_duration)}"
        )
        return SleepMetrics(
            ideal_duration=sleep_duration,
            ideal_bedtime=final_bedtime,
            ideal_wake_time=final_wake_time,
        )


    def suggest_wake_times_based_on_cycles(
        self,
        bedtime: time,
        min_cycles: int = 4,
        max_cycles: int = 6
    ) -> List[time]:
        """
        Suggests optimal wake-up times based on completing full sleep cycles.

        Assumes sleep onset time and cycle duration from configuration.

        Args:
            bedtime (time): The time the user intends to go to bed.
            min_cycles (int): Minimum number of sleep cycles to suggest (default: 4).
            max_cycles (int): Maximum number of sleep cycles to suggest (default: 6).

        Returns:
            List[time]: A list of suggested wake-up time objects, sorted chronologically.
        """
        if not isinstance(bedtime, time):
            logger.error(f"Invalid bedtime type: {type(bedtime)}. Expected datetime.time.")
            return []
        if not (1 <= min_cycles <= max_cycles <= 10): # Basic sanity check
             logger.error(f"Invalid cycle range: min={min_cycles}, max={max_cycles}")
             return []

        suggested_times: List[time] = []
        ref_date = date.today() # Arbitrary date for calculation
        bedtime_dt = datetime.combine(ref_date, bedtime)

        # Account for sleep onset time
        sleep_start_dt = bedtime_dt + timedelta(minutes=self._sleep_onset_minutes)

        for num_cycles in range(min_cycles, max_cycles + 1):
            total_sleep_duration = timedelta(minutes=num_cycles * self._sleep_cycle_duration_minutes)
            wake_dt = sleep_start_dt + total_sleep_duration
            suggested_times.append(wake_dt.time())
            logger.debug(f"Suggested wake time for {num_cycles} cycles (from {bedtime.strftime('%H:%M')}): {wake_dt.strftime('%H:%M')}")

        return sorted(suggested_times)


    def analyze_sleep_quality(
        self,
        recommended: SleepMetrics,
        sleep_start: datetime, # Expect timezone-aware
        sleep_end: datetime,   # Expect timezone-aware
        heart_rate_data: Optional[List[Tuple[datetime, int]]] = None,
        hrv_data: Optional[List[Tuple[datetime, float]]] = None, # Expect RMSSD in ms
        # movement_data: Optional[List[Tuple[datetime, float]]] = None # Future use
    ) -> SleepMetrics:
        """
        Analyzes sleep quality based on actual sleep times and physiological data.

        Compares actual sleep duration and timing against recommendations and
        evaluates heart rate and HRV data (if provided) against configured targets
        to produce an overall quality score (0-100).

        Args:
            recommended (SleepMetrics): The recommended sleep metrics for comparison.
            sleep_start (datetime): Actual time sleep began (timezone-aware).
            sleep_end (datetime): Actual time sleep ended (timezone-aware).
            heart_rate_data (Optional[List[Tuple[datetime, int]]]): List of
                (timestamp, bpm) tuples during sleep.
            hrv_data (Optional[List[Tuple[datetime, float]]]): List of
                (timestamp, rmssd_ms) tuples during sleep.

        Returns:
            SleepMetrics: An updated SleepMetrics object containing actual values,
                          sleep deficit, and the calculated quality score.

        Raises:
            ValueError: If input datetimes are invalid or recommendations are missing.
        """
        # --- Input Validation ---
        if not isinstance(recommended, SleepMetrics):
            raise ValueError("Recommended SleepMetrics object must be provided.")
        if not isinstance(sleep_start, datetime) or not isinstance(sleep_end, datetime):
            raise ValueError("sleep_start and sleep_end must be datetime objects.")
        if sleep_end <= sleep_start:
            raise ValueError("Sleep end time must be after sleep start time.")
        if sleep_start.tzinfo is None or sleep_end.tzinfo is None:
             logger.warning("Analyzing sleep quality with naive datetimes. Results may be inaccurate if timezone differs from recommendations.")
             # Consider converting to UTC or raising error if consistency needed

        logger.info(f"Analyzing sleep quality. Recommended: {recommended.ideal_bedtime.strftime('%H:%M')}-{recommended.ideal_wake_time.strftime('%H:%M')}")
        logger.info(f"Actual Sleep: {sleep_start} to {sleep_end}")

        # --- Calculate Actuals & Deficit ---
        actual_duration = sleep_end - sleep_start
        # Use local time for comparison with recommended times (which are also local)
        actual_bedtime = sleep_start.astimezone(None).time() # Convert to local time
        actual_wake_time = sleep_end.astimezone(None).time()
        sleep_deficit = recommended.ideal_duration - actual_duration

        # --- Calculate Score Components ---
        duration_score = self._calculate_duration_score(actual_duration, recommended.ideal_duration)
        timing_score = self._calculate_timing_score(actual_bedtime, actual_wake_time, recommended.ideal_bedtime, recommended.ideal_wake_time)
        physiological_score = self._calculate_physiological_score(heart_rate_data, hrv_data)

        # --- Combine Scores ---
        weights = self._quality_weights
        total_score = (
            duration_score * weights.get("duration", 0.0) +
            timing_score * weights.get("timing", 0.0) +
            physiological_score * weights.get("physiological", 0.0)
        )
        # Ensure score is within 0-100 range
        sleep_quality_score = max(0.0, min(100.0, total_score))

        logger.info(f"Sleep quality analysis complete. Overall Score: {sleep_quality_score:.1f}/100")

        # Return updated metrics object
        return SleepMetrics(
            ideal_duration=recommended.ideal_duration,
            ideal_bedtime=recommended.ideal_bedtime,
            ideal_wake_time=recommended.ideal_wake_time,
            actual_duration=actual_duration,
            actual_bedtime=actual_bedtime,
            actual_wake_time=actual_wake_time,
            sleep_quality_score=sleep_quality_score,
            # Deficit is calculated in __post_init__
        )

    def _calculate_duration_score(self, actual: timedelta, ideal: timedelta) -> float:
        """
        Calculates the duration component of the sleep quality score (0-100).

        Penalizes durations significantly shorter or longer than the ideal duration,
        based on configured tolerance and penalty range.
        """
        max_score = 100.0 # Score is relative, weighted later
        diff_minutes = abs(actual.total_seconds() - ideal.total_seconds()) / 60.0

        if diff_minutes <= self._duration_tolerance:
            score = max_score
        else:
            penalty = (diff_minutes - self._duration_tolerance) * (max_score / max(1, self._duration_penalty_range))
            score = max(0.0, max_score - penalty)
        logger.debug(f"Duration sub-score: {score:.1f} (Diff: {diff_minutes:.0f} min)")
        return score

    def _calculate_timing_score(self, actual_bed: time, actual_wake: time, ideal_bed: time, ideal_wake: time) -> float:
        """Calculates the timing component of the sleep quality score (0-100)."""
        max_score = 100.0 # Score is relative, weighted later
        max_part_score = max_score / 2.0 # Split score between bed and wake times

        actual_bed_m = time_to_total_minutes(actual_bed)
        ideal_bed_m = time_to_total_minutes(ideal_bed)
        actual_wake_m = time_to_total_minutes(actual_wake)
        ideal_wake_m = time_to_total_minutes(ideal_wake)

        # Calculate difference handling wrap-around midnight (1440 minutes)
        bed_diff_m = min(abs(actual_bed_m - ideal_bed_m), 1440 - abs(actual_bed_m - ideal_bed_m))
        wake_diff_m = min(abs(actual_wake_m - ideal_wake_m), 1440 - abs(actual_wake_m - ideal_wake_m))

        # Calculate score for bedtime
        if bed_diff_m <= self._timing_tolerance:
            bed_score = max_part_score
        else:
            penalty = (bed_diff_m - self._timing_tolerance) * (max_part_score / max(1, self._timing_penalty_range))
            bed_score = max(0.0, max_part_score - penalty)

        # Calculate score for wake time
        if wake_diff_m <= self._timing_tolerance:
            wake_score = max_part_score
        else:
            penalty = (wake_diff_m - self._timing_tolerance) * (max_part_score / max(1, self._timing_penalty_range))
            wake_score = max(0.0, max_part_score - penalty)

        total_timing_score = bed_score + wake_score
        logger.debug(f"Timing sub-score: {total_timing_score:.1f} (Bed diff: {bed_diff_m:.0f}m, Wake diff: {wake_diff_m:.0f}m)")
        return total_timing_score

    def _calculate_timing_score(self, actual_bed: time, actual_wake: time, ideal_bed: time, ideal_wake: time) -> float:
        """
        Calculates the timing component of the sleep quality score (0-100).

        Compares actual bedtime and wake time against ideals, handling midnight wrap-around.
        Penalizes deviations based on configured tolerance and penalty range.
        """
        max_score = 100.0 # Score is relative, weighted later
        max_part_score = max_score / 2.0 # Split score between bed and wake times

        actual_bed_m = time_to_total_minutes(actual_bed)
        ideal_bed_m = time_to_total_minutes(ideal_bed)
        actual_wake_m = time_to_total_minutes(actual_wake)
        ideal_wake_m = time_to_total_minutes(ideal_wake)

        # Calculate difference handling wrap-around midnight (1440 minutes)
        bed_diff_m = min(abs(actual_bed_m - ideal_bed_m), 1440 - abs(actual_bed_m - ideal_bed_m))
        wake_diff_m = min(abs(actual_wake_m - ideal_wake_m), 1440 - abs(actual_wake_m - ideal_wake_m))

        # Calculate score for bedtime
        if bed_diff_m <= self._timing_tolerance:
            bed_score = max_part_score
        else:
            penalty = (bed_diff_m - self._timing_tolerance) * (max_part_score / max(1, self._timing_penalty_range))
            bed_score = max(0.0, max_part_score - penalty)

        # Calculate score for wake time
        if wake_diff_m <= self._timing_tolerance:
            wake_score = max_part_score
        else:
            penalty = (wake_diff_m - self._timing_tolerance) * (max_part_score / max(1, self._timing_penalty_range))
            wake_score = max(0.0, max_part_score - penalty)

        total_timing_score = bed_score + wake_score
        logger.debug(f"Timing sub-score: {total_timing_score:.1f} (Bed diff: {bed_diff_m:.0f}m, Wake diff: {wake_diff_m:.0f}m)")
        return total_timing_score

    def _calculate_physiological_score(
        self,
        heart_rate_data: Optional[List[Tuple[datetime, int]]],
        hrv_data: Optional[List[Tuple[datetime, float]]]
    ) -> float:
        """
        Calculates the physiological component of the sleep quality score (0-100).

        Evaluates minimum heart rate and average HRV (RMSSD) against configured targets.
        Adjusts scoring based on available data (HR only, HRV only, or both).
        """
        max_score = 100.0 # Score is relative, weighted later
        hr_score = 0.0
        hrv_score = 0.0
        weights = self._physio_weights
        hr_weight = weights.get("hr", 0.5)
        hrv_weight = weights.get("hrv", 0.5)

        # Adjust weights if only one type of data is available
        has_hr = bool(heart_rate_data)
        has_hrv = bool(hrv_data)
        if not has_hr and not has_hrv:
            logger.debug("No physiological data available for scoring.")
            return 0.0
        elif has_hr and not has_hrv:
            hr_weight = 1.0
            hrv_weight = 0.0
        elif not has_hr and has_hrv:
            hr_weight = 0.0
            hrv_weight = 1.0

        # Calculate HR Score (based on minimum HR during sleep)
        if has_hr:
            try:
                valid_hrs = [hr for _, hr in heart_rate_data if hr > 0] # type: ignore
                if valid_hrs:
                    min_hr = min(valid_hrs)
                    max_part_score = max_score * hr_weight
                    if self._hr_target_min <= min_hr <= self._hr_target_max:
                        hr_score = max_part_score
                    elif min_hr < self._hr_target_min:
                        penalty = (self._hr_target_min - min_hr) * (max_part_score / max(1, self._hr_penalty_low))
                        hr_score = max(0.0, max_part_score - penalty)
                    else: # min_hr > self._hr_target_max
                        penalty = (min_hr - self._hr_target_max) * (max_part_score / max(1, self._hr_penalty_high))
                        hr_score = max(0.0, max_part_score - penalty)
                    logger.debug(f"HR score part: {hr_score:.1f} (Min HR: {min_hr})")
                else: logger.warning("No valid HR values found.")
            except Exception as e: logger.error(f"Error calculating HR score: {e}")

        # Calculate HRV Score (based on average RMSSD)
        if has_hrv:
            try:
                valid_hrvs = [hrv for _, hrv in hrv_data if hrv > 0] # type: ignore
                if valid_hrvs:
                    avg_hrv = sum(valid_hrvs) / len(valid_hrvs)
                    max_part_score = max_score * hrv_weight
                    # Simple scaling: score increases towards target, capped at max_part_score
                    hrv_score = min(max_part_score, max_part_score * (avg_hrv / max(1, self._hrv_target)) * self._hrv_scale)
                    hrv_score = max(0.0, hrv_score) # Ensure non-negative
                    logger.debug(f"HRV score part: {hrv_score:.1f} (Avg RMSSD: {avg_hrv:.1f}ms)")
                else: logger.warning("No valid HRV values found.")
            except Exception as e: logger.error(f"Error calculating HRV score: {e}")

        total_physio_score = hr_score + hrv_score
        logger.debug(f"Physiological sub-score: {total_physio_score:.1f}")
        return total_physio_score


# --- Example Usage ---
async def run_example():
    """Runs examples demonstrating SleepCalculator functionality."""
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Running SleepCalculator Example ---")

    calculator = SleepCalculator() # Use default config

    # --- Duration ---
    print("\n--- Duration Tests ---")
    d1 = calculator.get_recommended_sleep_duration(age=30, sleep_need_scale=50)
    d2 = calculator.get_recommended_sleep_duration(age=30, sleep_need_scale=75)
    d3 = calculator.get_recommended_sleep_duration(age=16, sleep_need_scale=40)
    print(f"Age 30, Scale 50: {format_timedelta(d1)}")
    print(f"Age 30, Scale 75: {format_timedelta(d2)}")
    print(f"Age 16, Scale 40: {format_timedelta(d3)}")

    # --- Window ---
    print("\n--- Window Tests ---")
    w1 = calculator.calculate_sleep_window(age=30, chronotype=Chronotype.INTERMEDIATE, target_wake_time=time(7, 0))
    w2 = calculator.calculate_sleep_window(age=30, chronotype=Chronotype.NIGHT_OWL, chronotype_scale=80)
    w3 = calculator.calculate_sleep_window(age=68, chronotype=Chronotype.EARLY_BIRD, sleep_need_scale=60)
    print(f"Intermediate, Wake 7:00 -> {w1}")
    print(f"Night Owl, Scale 80 -> {w2}")
    print(f"Senior Early Bird, Sleep Scale 60 -> {w3}")

    # --- Cycle Suggestions ---
    print("\n--- Cycle Suggestions (Bedtime 22:30) ---")
    suggestions = calculator.suggest_wake_times_based_on_cycles(bedtime=time(22, 30))
    print(f"Suggested wake times: {[t.strftime('%H:%M') for t in suggestions]}")

    # --- Quality Analysis ---
    print("\n--- Quality Analysis Test ---")
    recommended = w1 # Use intermediate window
    # Simulate actual sleep (timezone-aware UTC)
    start_utc = datetime(2024, 1, 10, 23, 15, tzinfo=timezone.utc) # Slept later
    end_utc = datetime(2024, 1, 11, 6, 45, tzinfo=timezone.utc)   # Woke earlier
    # Simulate HR data
    hr_data = [(start_utc + timedelta(minutes=i*10), random.randint(50, 65)) for i in range(int((end_utc-start_utc).total_seconds() / 600))]
    # Simulate HRV data
    hrv_data = [(start_utc + timedelta(minutes=i*30), random.uniform(35, 65)) for i in range(int((end_utc-start_utc).total_seconds() / 1800))]

    try:
        analyzed = calculator.analyze_sleep_quality(
            recommended=recommended, sleep_start=start_utc, sleep_end=end_utc,
            heart_rate_data=hr_data, hrv_data=hrv_data
        )
        print(f"Analyzed Metrics: {analyzed}")
    except ValueError as e:
        print(f"Analysis Error: {e}")

if __name__ == "__main__":
    import asyncio

    asyncio.run(run_example())
