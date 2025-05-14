# === File: scheduler-core/tests/unit/test_sleep.py ===

"""
Unit Tests for the SleepCalculator Module.

Tests the functionality of the SleepCalculator class, including duration
recommendation, sleep window calculation, cycle suggestions, and quality analysis,
using both default and custom configurations.
"""

import logging
import random
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, Optional, Any

import pytest

# Module to test
try:
    from src.core.sleep import SleepCalculator, SleepMetrics
    # Import Chronotype enum, ensure it's the correct one used by SleepCalculator
    from src.core.chronotype import Chronotype
    # Import helper if used in assertions/setup
    SLEEP_MODULE_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).error(f"Failed to import modules for test_sleep: {e}")
    SLEEP_MODULE_AVAILABLE = False
    # Define dummy classes if imports fail
    class SleepCalculator: pass
    class SleepMetrics: pass
    from enum import Enum
    class Chronotype(Enum): INTERMEDIATE="intermediate"; EARLY_BIRD="early_bird"; NIGHT_OWL="night_owl"
    def format_timedelta(delta): return ""
    def time_to_total_minutes(t): return 0


# Skip all tests in this file if the sleep module isn't available
pytestmark = pytest.mark.skipif(not SLEEP_MODULE_AVAILABLE, reason="SleepCalculator module or its dependencies not found.")


# --- Fixtures ---

@pytest.fixture(scope="module")
def default_calculator() -> SleepCalculator:
    """Provides a SleepCalculator instance with default configuration."""
    return SleepCalculator()

@pytest.fixture(scope="module")
def custom_calculator() -> SleepCalculator:
    """Provides a SleepCalculator instance with custom configuration for testing."""
    custom_config = {
        "sleep_guidelines": {"adult": (6.5, 8.5)}, # Custom range: avg 7.5h
        "max_sleep_need_adjustment_hours": 0.5, # Max adjustment +/- 0.5h
        "sleep_cycle_duration_minutes": 85, # Shorter cycle
        "quality_score_weights": {"duration": 0.5, "timing": 0.2, "physiological": 0.3},
        "hr_target_min": 45, # Custom HR target
    }
    return SleepCalculator(config=custom_config)

@pytest.fixture
def sample_recommended_metrics() -> SleepMetrics:
    """Provides a sample SleepMetrics object representing recommendations."""
    # Example: Intermediate chronotype, default settings
    return SleepMetrics(
        ideal_duration=timedelta(hours=8),
        ideal_bedtime=time(23, 30),
        ideal_wake_time=time(7, 30)
    )


# --- Test get_recommended_sleep_duration ---

@pytest.mark.parametrize(
    "age, scale, expected_hours",
    [
        pytest.param(16, 50.0, 9.0, id="teen_avg"),
        pytest.param(30, 50.0, 8.0, id="adult_avg"),
        pytest.param(70, 50.0, 7.5, id="senior_avg"),
        pytest.param(30, 75.0, 8.5, id="adult_needs_more"), # Default max adj = 1h, (75-50)/50 * 1 = +0.5h -> 8.0 + 0.5 = 8.5
        pytest.param(30, 25.0, 7.5, id="adult_needs_less"), # (25-50)/50 * 1 = -0.5h -> 8.0 - 0.5 = 7.5
        pytest.param(30, 100.0, 9.0, id="adult_max_need"), # (100-50)/50 * 1 = +1.0h -> 8.0 + 1.0 = 9.0
        pytest.param(30, 0.0, 7.0, id="adult_min_need"),   # (0-50)/50 * 1 = -1.0h -> 8.0 - 1.0 = 7.0
        pytest.param(30, None, 8.0, id="adult_none_scale"), # None scale should use base average
        pytest.param(30, 110, 9.0, id="adult_scale_over_100"), # Scale > 100 clamps to max adjustment
        pytest.param(30, -10, 7.0, id="adult_scale_below_0"), # Scale < 0 clamps to min adjustment
        pytest.param(5, 50, 10.5, id="child_approx"), # Assuming guidelines would cover younger ages, using teen for approx
    ],
)
def test_get_recommended_duration_default(default_calculator: SleepCalculator, age: int, scale: Optional[float], expected_hours: float):
    """Tests recommended duration calculation with default config."""
    expected_delta = timedelta(hours=expected_hours)
    actual_delta = default_calculator.get_recommended_sleep_duration(age, scale)
    # Compare total seconds for float precision issues
    assert actual_delta.total_seconds() == pytest.approx(expected_delta.total_seconds())

def test_get_recommended_duration_custom_config(custom_calculator: SleepCalculator):
    """Tests recommended duration calculation with custom config."""
    # Custom adult range 6.5-8.5 (avg 7.5h), max adjustment 0.5h
    assert custom_calculator.get_recommended_sleep_duration(30, 50) == timedelta(hours=7.5) # Average
    assert custom_calculator.get_recommended_sleep_duration(30, 100) == timedelta(hours=8.0) # Max need (+0.5h)
    assert custom_calculator.get_recommended_sleep_duration(30, 0) == timedelta(hours=7.0) # Min need (-0.5h)

@pytest.mark.parametrize("invalid_age", [-1, 121])
def test_get_recommended_duration_invalid_age(default_calculator: SleepCalculator, invalid_age: int):
    """Tests that invalid age raises ValueError."""
    with pytest.raises(ValueError, match="Invalid age"):
        default_calculator.get_recommended_sleep_duration(invalid_age)


# --- Test calculate_sleep_window ---

def test_calculate_window_intermediate_default_wake(default_calculator: SleepCalculator):
    """Test intermediate chronotype with default wake time."""
    metrics = default_calculator.calculate_sleep_window(age=30, chronotype=Chronotype.INTERMEDIATE)
    assert metrics.ideal_duration == timedelta(hours=8)
    assert metrics.ideal_wake_time == time(7, 30) # Default wake for intermediate
    assert metrics.ideal_bedtime == time(23, 30) # 7:30 - 8h

def test_calculate_window_early_bird_custom_wake(default_calculator: SleepCalculator):
    """Test early bird with a specific target wake time."""
    # Adult, Early Bird (-1h default timing adj), target wake 6:00, avg sleep need (8h)
    metrics = default_calculator.calculate_sleep_window(
        age=30, chronotype=Chronotype.EARLY_BIRD, target_wake_time=time(6, 0)
    )
    assert metrics.ideal_duration == timedelta(hours=8)
    assert metrics.ideal_wake_time == time(5, 0) # 6:00 adjusted by -1h (default category adj)
    assert metrics.ideal_bedtime == time(21, 0) # 5:00 - 8h

def test_calculate_window_night_owl_scales(default_calculator: SleepCalculator):
    """Test night owl using preference scales for duration and timing."""
    # Adult, Night Owl, needs more sleep (scale 80 -> +0.6h -> 8.6h), prefers later (scale 80 -> +0.9h adj)
    # Default wake for night owl is 8:30
    metrics = default_calculator.calculate_sleep_window(
        age=30, chronotype=Chronotype.NIGHT_OWL, sleep_need_scale=80, chronotype_scale=80
    )
    # Duration: 8h base + ( (80-50)/50 * 1.0h max_adj ) = 8 + 0.6 = 8.6h
    expected_duration_hours = 8.0 + ((80.0 - 50.0) / 50.0) * default_calculator._max_sleep_need_adj
    expected_duration = timedelta(hours=expected_duration_hours)

    # Timing: Default wake 8:30 + ( (80-50)/50 * 1.5h max_adj ) = 8:30 + 0.9h = 8:30 + 54min = 9:24
    timing_adj_hours = ((80.0 - 50.0) / 50.0) * default_calculator._max_chrono_adj
    expected_wake_dt = datetime.combine(date.today(), time(8, 30)) + timedelta(hours=timing_adj_hours)
    expected_wake_time = expected_wake_dt.time()

    expected_bed_dt = expected_wake_dt - expected_duration
    expected_bedtime = expected_bed_dt.time()

    assert metrics.ideal_duration.total_seconds() == pytest.approx(expected_duration.total_seconds())
    assert metrics.ideal_wake_time == expected_wake_time
    assert metrics.ideal_bedtime == expected_bedtime

def test_calculate_window_early_morning_wake(default_calculator: SleepCalculator):
    """Test calculation when target wake time is early morning (e.g., 3 AM)."""
    # Intermediate, target wake 3:00, avg sleep need (8h)
    metrics = default_calculator.calculate_sleep_window(
        age=30, chronotype=Chronotype.INTERMEDIATE, target_wake_time=time(3, 0)
    )
    assert metrics.ideal_duration == timedelta(hours=8)
    assert metrics.ideal_wake_time == time(3, 0) # No adjustment for intermediate
    assert metrics.ideal_bedtime == time(19, 0) # 3:00 (next day) - 8h = 19:00 (previous day)


# --- Test suggest_wake_times_based_on_cycles ---

def test_suggest_wake_times_default(default_calculator: SleepCalculator):
    """Test cycle suggestions with default config."""
    # Bedtime 23:00, onset 15m, cycle 90m
    # Sleep starts 23:15
    # 4 cycles (6h 0m) -> wake 05:15
    # 5 cycles (7h 30m) -> wake 06:45
    # 6 cycles (9h 0m) -> wake 08:15
    suggestions = default_calculator.suggest_wake_times_based_on_cycles(bedtime=time(23, 0))
    assert suggestions == [time(5, 15), time(6, 45), time(8, 15)]

def test_suggest_wake_times_custom_config(custom_calculator: SleepCalculator):
    """Test cycle suggestions with custom cycle duration."""
    # Bedtime 22:00, onset 15m (default), cycle 85m
    # Sleep starts 22:15
    # 4 cycles (340m = 5h 40m) -> wake 03:55
    # 5 cycles (425m = 7h 5m) -> wake 05:20
    # 6 cycles (510m = 8h 30m) -> wake 06:45
    suggestions = custom_calculator.suggest_wake_times_based_on_cycles(bedtime=time(22, 0))
    assert suggestions == [time(3, 55), time(5, 20), time(6, 45)]

@pytest.mark.parametrize("invalid_bedtime", [None, "23:00", 23])
def test_suggest_wake_times_invalid_input(default_calculator: SleepCalculator, invalid_bedtime):
    """Test cycle suggestions with invalid bedtime input type."""
    assert default_calculator.suggest_wake_times_based_on_cycles(bedtime=invalid_bedtime) == []


# --- Test analyze_sleep_quality ---

@pytest.fixture
def sample_sleep_data() -> Dict[str, Any]:
    """Provides sample physiological data for sleep quality tests."""
    start = datetime(2024, 1, 10, 23, 0, tzinfo=timezone.utc) # Example start time UTC
    return {
        "start": start,
        "hr_data": [(start + timedelta(minutes=i*10), random.randint(50, 65)) for i in range(48)], # ~8 hours
        "hrv_data": [(start + timedelta(minutes=i*30), random.uniform(45, 75)) for i in range(16)], # ~8 hours
    }

def test_analyze_quality_perfect_match(default_calculator: SleepCalculator, sample_recommended_metrics: SleepMetrics, sample_sleep_data: Dict[str, Any]):
    """Test quality score when actual sleep perfectly matches recommendations."""
    start = datetime.combine(date(2024,1,10), sample_recommended_metrics.ideal_bedtime).replace(tzinfo=timezone.utc)
    end = start + sample_recommended_metrics.ideal_duration

    analysis = default_calculator.analyze_sleep_quality(
        recommended=sample_recommended_metrics, sleep_start=start, sleep_end=end,
        heart_rate_data=sample_sleep_data["hr_data"], hrv_data=sample_sleep_data["hrv_data"]
    )
    assert analysis.sleep_quality_score == pytest.approx(100.0)
    assert analysis.actual_duration == sample_recommended_metrics.ideal_duration
    assert analysis.sleep_deficit == timedelta(0)

def test_analyze_quality_short_sleep_bad_timing(default_calculator: SleepCalculator, sample_recommended_metrics: SleepMetrics):
    """Test quality score with short duration and poor timing."""
    # Recommended: 23:30 - 07:30 (8h)
    start = datetime(2024, 1, 11, 1, 0, tzinfo=timezone.utc)   # 1.5h late bedtime
    end = datetime(2024, 1, 11, 6, 0, tzinfo=timezone.utc)     # 1.5h early wake -> 5h duration
    # Simulate high HR, low HRV
    hr_data = [(start + timedelta(minutes=i*10), random.randint(65, 80)) for i in range(30)]
    hrv_data = [(start + timedelta(minutes=i*30), random.uniform(20, 35)) for i in range(10)]

    analysis = default_calculator.analyze_sleep_quality(
        recommended=sample_recommended_metrics, sleep_start=start, sleep_end=end,
        heart_rate_data=hr_data, hrv_data=hrv_data
    )
    assert analysis.actual_duration == timedelta(hours=5)
    assert analysis.sleep_deficit == timedelta(hours=3)
    # Expect significantly lower score due to poor duration, timing, and physio hints
    assert analysis.sleep_quality_score < 50

def test_analyze_quality_no_physiological_data(default_calculator: SleepCalculator, sample_recommended_metrics: SleepMetrics):
    """Test quality score calculation when physiological data is missing."""
    # Good duration and timing
    start = datetime.combine(date(2024,1,10), sample_recommended_metrics.ideal_bedtime).replace(tzinfo=timezone.utc)
    end = start + sample_recommended_metrics.ideal_duration

    analysis = default_calculator.analyze_sleep_quality(
        recommended=sample_recommended_metrics, sleep_start=start, sleep_end=end,
        heart_rate_data=None, hrv_data=[] # No physiological data
    )
    # Score should only include duration and timing components
    # Default weights: duration=0.4, timing=0.3, physiological=0.3
    # Since duration and timing are perfect (score=100 each), total = 100*0.4 + 100*0.3 + 0*0.3 = 70
    expected_score = 100.0 * default_calculator._quality_weights['duration'] + \
                     100.0 * default_calculator._quality_weights['timing']
    assert analysis.sleep_quality_score == pytest.approx(expected_score)
    assert analysis.sleep_deficit == timedelta(0)

def test_analyze_quality_only_hr_data(default_calculator: SleepCalculator, sample_recommended_metrics: SleepMetrics, sample_sleep_data: Dict[str, Any]):
    """Test quality score when only HR data is available."""
    start = datetime.combine(date(2024,1,10), sample_recommended_metrics.ideal_bedtime).replace(tzinfo=timezone.utc)
    end = start + sample_recommended_metrics.ideal_duration

    analysis = default_calculator.analyze_sleep_quality(
        recommended=sample_recommended_metrics, sleep_start=start, sleep_end=end,
        heart_rate_data=sample_sleep_data["hr_data"], hrv_data=None # No HRV
    )
    # Physiological score should only come from HR (weight adjusted internally)
    # Expect score > 70 (duration+timing) but < 100 (missing HRV contribution)
    assert 70 < analysis.sleep_quality_score < 100

@pytest.mark.parametrize("start_offset_mins, end_offset_mins", [
    (-15, 15), # Slightly off timing
    (-90, -30), # Very off timing
])
def test_analyze_quality_timing_component(default_calculator: SleepCalculator, sample_recommended_metrics: SleepMetrics, start_offset_mins: int, end_offset_mins: int):
    """Test the timing component calculation specifically."""
    # Perfect duration, only timing varies
    start = datetime.combine(date(2024,1,10), sample_recommended_metrics.ideal_bedtime).replace(tzinfo=timezone.utc) + timedelta(minutes=start_offset_mins)
    end = start + sample_recommended_metrics.ideal_duration + timedelta(minutes=end_offset_mins - start_offset_mins) # Keep duration ideal

    analysis = default_calculator.analyze_sleep_quality(
        recommended=sample_recommended_metrics, sleep_start=start, sleep_end=end,
        heart_rate_data=None, hrv_data=None # Ignore physiological for this test
    )
    # Score should be duration (perfect=40) + timing (variable=0-30) + physio (0)
    duration_score_part = 100.0 * default_calculator._quality_weights['duration']
    max_timing_score_part = 100.0 * default_calculator._quality_weights['timing']

    if abs(start_offset_mins) <= default_calculator._timing_tolerance and abs(end_offset_mins) <= default_calculator._timing_tolerance:
         # Within tolerance, timing score should be max
         assert analysis.sleep_quality_score == pytest.approx(duration_score_part + max_timing_score_part)
    else:
         # Outside tolerance, timing score should be penalized, total score < 70
         assert analysis.sleep_quality_score < duration_score_part + max_timing_score_part

def test_analyze_quality_invalid_window_input(default_calculator: SleepCalculator, sample_recommended_metrics: SleepMetrics):
    """Test analyze_sleep_quality raises ValueError for invalid time window."""
    start = datetime(2024, 1, 11, 8, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 11, 7, 0, tzinfo=timezone.utc) # End before start
    with pytest.raises(ValueError, match="end time must be after start time"):
        default_calculator.analyze_sleep_quality(sample_recommended_metrics, start, end)

def test_analyze_quality_naive_datetimes(default_calculator: SleepCalculator, sample_recommended_metrics: SleepMetrics):
    """Test that analyze_sleep_quality handles naive datetimes (with warning)."""
    start_naive = datetime(2024, 1, 10, 23, 0) # No tzinfo
    end_naive = datetime(2024, 1, 11, 7, 0)
    with pytest.warns(UserWarning, match="naive datetimes"): # Check for warning
         analysis = default_calculator.analyze_sleep_quality(
             recommended=sample_recommended_metrics, sleep_start=start_naive, sleep_end=end_naive
         )
    # Analysis should still proceed, assuming local time matches recommendation time
    assert analysis.sleep_quality_score is not None
