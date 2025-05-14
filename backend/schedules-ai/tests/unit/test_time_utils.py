# === File: scheduler-core/tests/unit/test_time_utils.py ===

"""
Unit Tests for the time_utils Module.

Verifies the correctness of time parsing, formatting, timezone handling,
and calculation helper functions provided in src.utils.time_utils.
"""

import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Dict, Union, Any

import pytest

# Attempt to import pytz to check availability for timezone tests
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    pytz = None # Placeholder

# Import functions to test using absolute paths
try:
    from src.utils.time_utils import (
        DEFAULT_TIMEZONE_STR,
        PYTZ_AVAILABLE as UTILS_PYTZ_AVAILABLE, # Check if utils detected pytz
        calculate_end_time,
        combine_date_time_tz,
        format_time_object,
        format_timedelta,
        get_current_time_in_tz,
        get_timezone,
        parse_duration_string,
        parse_time_string,
        time_to_total_minutes,
        total_minutes_to_time,
    )
    TIME_UTILS_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).critical(f"Failed to import time_utils for testing: {e}", exc_info=True)
    TIME_UTILS_AVAILABLE = False

# Skip all tests if the module itself cannot be imported
pytestmark = pytest.mark.skipif(not TIME_UTILS_AVAILABLE, reason="src.utils.time_utils module not found.")


# --- Test get_timezone ---

@pytest.mark.skipif(not PYTZ_AVAILABLE, reason="pytz library not installed, skipping named timezone tests.")
def test_get_timezone_valid_pytz():
    """Test getting a valid pytz timezone."""
    tz = get_timezone("Europe/Warsaw")
    assert isinstance(tz, pytz.tzinfo.BaseTzInfo)
    assert "Warsaw" in str(tz)

@pytest.mark.skipif(not PYTZ_AVAILABLE, reason="pytz library not installed.")
def test_get_timezone_invalid_pytz():
    """Test getting an invalid pytz timezone defaults to UTC."""
    tz = get_timezone("Invalid/Timezone")
    assert tz is pytz.utc

def test_get_timezone_utc():
    """Test getting the UTC timezone (works with or without pytz)."""
    tz = get_timezone("UTC")
    assert tz is timezone.utc or tz is pytz.utc # Allow either standard UTC or pytz UTC

def test_get_timezone_none_defaults_to_utc():
    """Test that None defaults to UTC."""
    tz = get_timezone(None)
    # Check against DEFAULT_TIMEZONE_STR if needed, but assuming it's UTC
    assert tz is timezone.utc or tz is pytz.utc

@pytest.mark.skipif(PYTZ_AVAILABLE, reason="Test only runs when pytz is NOT installed.")
def test_get_timezone_no_pytz_named_defaults_utc():
    """Test getting named timezone defaults to UTC when pytz is unavailable."""
    tz = get_timezone("Europe/Warsaw")
    assert tz is timezone.utc


# --- Test get_current_time_in_tz ---

def test_get_current_time_in_tz():
    """Test getting current time in a specific timezone."""
    # This test is sensitive to the exact moment it runs, focus on type and tzinfo
    now_utc = get_current_time_in_tz("UTC")
    assert isinstance(now_utc, datetime)
    assert now_utc.tzinfo is not None
    assert now_utc.tzinfo.utcoffset(now_utc) == timedelta(0)

    if PYTZ_AVAILABLE:
        now_warsaw = get_current_time_in_tz("Europe/Warsaw")
        assert isinstance(now_warsaw, datetime)
        assert now_warsaw.tzinfo is not None
        # Check offset is plausible for Warsaw (CET/CEST)
        assert now_warsaw.tzinfo.utcoffset(now_warsaw) in [timedelta(hours=1), timedelta(hours=2)]


# --- Test parse_time_string ---

@pytest.mark.parametrize(
    "time_str, fmt, expected",
    [
        ("09:30", "%H:%M", time(9, 30)),
        ("00:00", "%H:%M", time(0, 0)),
        ("23:59", "%H:%M", time(23, 59)),
        ("14:05", "%H:%M", time(14, 5)),
        (" 15:10 ", "%H:%M", time(15, 10)), # With spaces
        ("08:15:30", "%H:%M:%S", time(8, 15, 30)),
        ("3:05 PM", "%I:%M %p", time(15, 5)),
    ],
    ids=["std", "midnight", "end_of_day", "leading_zero", "spaces", "with_seconds", "am_pm"]
)
def test_parse_time_string_valid(time_str: str, fmt: str, expected: time):
    """Test parsing valid time strings with default and custom formats."""
    assert parse_time_string(time_str, fmt=fmt) == expected

@pytest.mark.parametrize(
    "time_str, fmt",
    [
        ("24:00", "%H:%M"), # Invalid hour
        ("9:30", "%H:%M"),  # Missing leading zero for %H
        ("09:60", "%H:%M"), # Invalid minute
        ("abc", "%H:%M"),   # Non-numeric
        ("", "%H:%M"),      # Empty string
        (None, "%H:%M"),    # None input
        (1230, "%H:%M"),    # Wrong type
        ("14:30", "%H-%M"), # Wrong format
    ],
    ids=["invalid_hour", "no_leading_zero", "invalid_minute", "alpha", "empty", "none", "wrong_type", "wrong_format"]
)
def test_parse_time_string_invalid(time_str: Optional[str], fmt: str):
    """Test parsing invalid time strings or inputs."""
    assert parse_time_string(time_str, fmt=fmt) is None


# --- Test format_time_object ---

@pytest.mark.parametrize(
    "time_obj, fmt, expected",
    [
        (time(16, 45), "%H:%M", "16:45"),
        (time(0, 5), "%H:%M", "00:05"),
        (time(23, 59, 59), "%H:%M:%S", "23:59:59"),
        (time(8, 15), "%I:%M %p", "08:15 AM"),
        (time(20, 30), "%I:%M %p", "08:30 PM"),
    ],
    ids=["std_hm", "leading_zero_m", "with_seconds", "am", "pm"]
)
def test_format_time_object_valid(time_obj: time, fmt: str, expected: str):
    """Test formatting valid time objects."""
    assert format_time_object(time_obj, fmt=fmt) == expected

def test_format_time_object_none():
    """Test formatting None returns 'N/A'."""
    assert format_time_object(None) == "N/A"

def test_format_time_object_invalid_type():
    """Test formatting an invalid type returns 'N/A'."""
    assert format_time_object("10:00") == "N/A" # type: ignore


# --- Test combine_date_time_tz ---

def test_combine_date_time_tz_utc():
    """Test combining date/time with UTC timezone."""
    d = date(2024, 5, 15)
    t = time(10, 30)
    dt_aware = combine_date_time_tz(d, t, "UTC")
    assert isinstance(dt_aware, datetime)
    assert dt_aware.date() == d
    assert dt_aware.time() == t
    assert dt_aware.tzinfo is not None
    assert dt_aware.tzinfo.utcoffset(dt_aware) == timedelta(0)

@pytest.mark.skipif(not PYTZ_AVAILABLE, reason="pytz library not installed.")
def test_combine_date_time_tz_named_pytz():
    """Test combining date/time with a named timezone using pytz."""
    d = date(2024, 7, 20) # Summer time
    t = time(14, 0)
    dt_aware = combine_date_time_tz(d, t, "Europe/Warsaw")
    assert isinstance(dt_aware, datetime)
    assert dt_aware.date() == d
    assert dt_aware.time() == t
    assert dt_aware.tzinfo is not None
    assert dt_aware.tzinfo.utcoffset(dt_aware) == timedelta(hours=2) # CEST

@pytest.mark.skipif(PYTZ_AVAILABLE, reason="Test only runs when pytz is NOT installed.")
def test_combine_date_time_tz_named_no_pytz():
    """Test combining with named timezone defaults to UTC when pytz is unavailable."""
    d = date(2024, 7, 20)
    t = time(14, 0)
    dt_aware = combine_date_time_tz(d, t, "Europe/Warsaw")
    assert isinstance(dt_aware, datetime)
    assert dt_aware.tzinfo is timezone.utc # Should default to UTC

def test_combine_date_time_tz_invalid_input():
    """Test combining with invalid date/time inputs."""
    assert combine_date_time_tz(None, time(10,0)) is None # type: ignore
    assert combine_date_time_tz(date(2024,1,1), None) is None # type: ignore


# --- Test calculate_end_time ---

@pytest.mark.parametrize(
    "start_h, start_m, dur_h, dur_m, exp_h, exp_m",
    [
        (9, 0, 2, 30, 11, 30),      # No wrap
        (22, 30, 3, 0, 1, 30),       # Wrap midnight
        (14, 0, 0, 0, 14, 0),       # Zero duration
        (23, 59, 0, 1, 0, 0),       # Wrap exactly at midnight
        (10, 15, 0, -30, 9, 45),     # Negative duration
    ],
    ids=["no_wrap", "wrap", "zero_dur", "exact_wrap", "neg_dur"]
)
def test_calculate_end_time(start_h, start_m, dur_h, dur_m, exp_h, exp_m):
    """Test calculating end time with various durations and wrap-around."""
    start = time(start_h, start_m)
    duration = timedelta(hours=dur_h, minutes=dur_m)
    expected = time(exp_h, exp_m)
    assert calculate_end_time(start, duration) == expected

def test_calculate_end_time_invalid_input():
    """Test calculate_end_time with invalid input types."""
    assert calculate_end_time("10:00", timedelta(hours=1)) is None # type: ignore
    assert calculate_end_time(time(10,0), 60) is None # type: ignore


# --- Test format_timedelta ---

@pytest.mark.parametrize(
    "delta_args, show_seconds, expected",
    [
        ({"hours": 2, "minutes": 30}, False, "2h 30m"),
        ({"minutes": 45}, False, "45m"),
        ({"hours": 1}, False, "1h"),
        ({"days": 1, "hours": 3}, False, "27h 0m"), # Shows total hours/minutes
        ({"seconds": 30}, False, "<1m"), # Seconds ignored by default if < 1m
        ({"seconds": 30}, True, "30s"), # Seconds shown if requested and < 1m
        ({"minutes": 1, "seconds": 15}, False, "1m"), # Seconds ignored if minutes present
        ({"minutes": 1, "seconds": 15}, True, "1m"), # Seconds still ignored if minutes present
        ({"seconds": 0}, False, "0m"),
        (None, False, "N/A"),
        ({"hours": -1, "minutes": -15}, False, "-1h 15m"), # Negative duration
    ],
    ids=["h_m", "m_only", "h_only", "days", "s_only_noshow", "s_only_show", "m_s_noshow", "m_s_show", "zero", "none", "negative"]
)
def test_format_timedelta(delta_args: Optional[Dict], show_seconds: bool, expected: str):
    """Test formatting timedelta objects."""
    delta = timedelta(**delta_args) if delta_args is not None else None
    assert format_timedelta(delta, show_seconds=show_seconds) == expected

def test_format_timedelta_invalid_type():
    """Test formatting invalid type returns 'Invalid'."""
    assert format_timedelta("1h") == "Invalid" # type: ignore


# --- Test parse_duration_string ---

@pytest.mark.parametrize(
    "duration_str, expected_minutes",
    [
        ("1h 30m", 90),
        ("45m", 45),
        ("2h", 120),
        (" 1 h ", 60),
        (" 5 m ", 5),
        ("1h30m", 90),
        ("120", 120), # Assume minutes
        ("1.5h", 90),
        ("0.5h", 30),
        ("2.25 h", 135),
        ("1h 15", 75), # Assume 15 is minutes
        ("60s", 0), # Seconds ignored, results in 0 minutes
        ("1m 30s", 1), # Seconds ignored
    ],
    ids=["h_m", "m_only", "h_only", "spaces", "m_spaces", "no_spaces", "num_only", "float_h", "half_h", "float_h_space", "h_num", "s_only", "m_s"]
)
def test_parse_duration_string_valid(duration_str: str, expected_minutes: int):
    """Test parsing valid duration strings."""
    expected_delta = timedelta(minutes=expected_minutes)
    assert parse_duration_string(duration_str) == expected_delta

@pytest.mark.parametrize(
    "duration_str",
    ["abc", "", None, "1 hour", "2 days", "1h 5x", "-30m", "1h -15m"],
    ids=["alpha", "empty", "none", "word_unit", "day_unit", "invalid_unit", "negative_num", "mixed_sign"]
)
def test_parse_duration_string_invalid(duration_str: Optional[str]):
    """Test parsing invalid duration strings."""
    assert parse_duration_string(duration_str) is None


# --- Test time_to_total_minutes ---

@pytest.mark.parametrize(
    "time_in, expected_minutes",
    [
        (time(0, 0), 0),
        (time(1, 0), 60),
        (time(15, 45), 945),
        (time(23, 59), 1439),
    ]
)
def test_time_to_total_minutes_valid(time_in: time, expected_minutes: int):
    """Test converting time objects to total minutes."""
    assert time_to_total_minutes(time_in) == expected_minutes

def test_time_to_total_minutes_invalid():
    """Test converting invalid input returns None."""
    assert time_to_total_minutes(None) is None
    assert time_to_total_minutes("10:00") is None # type: ignore


# --- Test total_minutes_to_time ---

@pytest.mark.parametrize(
    "minutes_in, expected_time",
    [
        (0, time(0, 0)),
        (60, time(1, 0)),
        (945, time(15, 45)),
        (1439, time(23, 59)),
        (1440, time(0, 0)), # 1440 should map to 00:00
        (75.8, time(1, 16)), # Floats should be rounded
        (75.2, time(1, 15)), # Floats should be rounded
    ]
)
def test_total_minutes_to_time_valid(minutes_in: Union[int, float], expected_time: time):
    """Test converting total minutes to time objects."""
    assert total_minutes_to_time(minutes_in) == expected_time

@pytest.mark.parametrize(
    "minutes_in", [-1, 1441, None, "abc"], ids=["negative", "too_high", "none", "wrong_type"]
)
def test_total_minutes_to_time_invalid(minutes_in: Any):
    """Test converting invalid minute inputs returns None (or raises error depending on strictness)."""
    # The refactored version clamps and logs warning for out-of-range, returns None for wrong type/None
    if minutes_in == -1:
         assert total_minutes_to_time(minutes_in) == time(0,0) # Clamped to 0
    elif minutes_in == 1441:
         assert total_minutes_to_time(minutes_in) == time(0,0) # Clamped to 1440 -> 00:00
    else:
         assert total_minutes_to_time(minutes_in) is None # Wrong type or None


# --- Example Runner ---
async def run_example():
    """Placeholder async runner for consistency if needed."""
    pass # No async functions to run here directly

if __name__ == "__main__":
    # You can run pytest directly on this file
    print("Run this file with pytest to execute tests.")
    # Example of manually running one test (less common)
    # test_parse_duration_string_valid("1.5h", 90)
