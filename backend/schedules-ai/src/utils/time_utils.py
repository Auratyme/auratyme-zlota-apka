# === Plik: scheduler-core/src/utils/time_utils.py ===

"""
Time Utility Functions.

Provides helper functions for common time-related operations, including parsing,
formatting, timezone handling, and calculations involving time, datetime, and
timedelta objects. Ensures consistent handling of timezones where applicable.
"""

import logging
import re
from datetime import date, datetime, time, timedelta, tzinfo, timezone  # Dodano import timezone
from typing import Optional, Union

# Third-party imports
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "pytz library not found. Timezone functionality will be limited to UTC. "
        "Install with: poetry add pytz"
    )

logger = logging.getLogger(__name__)

# Default timezone if none is specified or pytz is unavailable
DEFAULT_TIMEZONE_STR = "UTC"


def get_timezone(tz_name: Optional[str] = None) -> tzinfo:
    """
    Gets a timezone object (datetime.timezone or pytz timezone).

    Prefers pytz if available for named timezones, otherwise uses datetime.timezone.utc.

    Args:
        tz_name (Optional[str]): The IANA timezone name (e.g., 'Europe/Warsaw', 'UTC',
                                 'America/New_York'). If None or invalid, defaults to UTC.

    Returns:
        tzinfo: A timezone object (either pytz timezone or datetime.timezone.utc).
    """
    target_tz_name = tz_name or DEFAULT_TIMEZONE_STR

    if PYTZ_AVAILABLE:
        try:
            return pytz.timezone(target_tz_name)
        except pytz.UnknownTimeZoneError:
            logger.warning(f"Unknown pytz timezone '{target_tz_name}'. Defaulting to UTC.")
            return pytz.utc
    else:
        # Fallback to standard library timezone (only UTC reliably supported by name)
        if target_tz_name.upper() == "UTC":
            return timezone.utc
        else:
            logger.warning(f"pytz not installed. Cannot get named timezone '{target_tz_name}'. Defaulting to UTC.")
            return timezone.utc


def get_current_time_in_tz(tz_name: Optional[str] = None) -> datetime:
    """
    Gets the current time, localized to the specified timezone.

    Args:
        tz_name (Optional[str]): The target IANA timezone name. Defaults to UTC.

    Returns:
        datetime: The current timezone-aware datetime object.
    """
    tz = get_timezone(tz_name)
    return datetime.now(tz)


def parse_time_string(time_str: str, fmt: str = "%H:%M") -> Optional[time]:
    """
    Parses a time string into a datetime.time object using a specified format.

    Args:
        time_str (str): The time string to parse (e.g., "14:30", "09:05:00").
        fmt (str): The format code expected for the time string (default: "%H:%M").

    Returns:
        Optional[time]: A time object if parsing is successful, otherwise None.
    """
    if not isinstance(time_str, str):
        logger.error(f"Invalid input type for parse_time_string: {type(time_str)}. Expected string.")
        return None
    try:
        return datetime.strptime(time_str.strip(), fmt).time()
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to parse time string '{time_str}' with format '{fmt}': {e}")
        return None


def format_time_object(time_obj: Optional[time], fmt: str = "%H:%M") -> str:
    """
    Formats a datetime.time object into a string.

    Args:
        time_obj (Optional[time]): The time object to format.
        fmt (str): The desired output format string (default: "%H:%M").

    Returns:
        str: The formatted time string, or "N/A" if input is None or invalid.
    """
    if time_obj is None:
        return "N/A"
    if not isinstance(time_obj, time):
        logger.error(f"Invalid input type for format_time_object: {type(time_obj)}. Expected time.")
        return "N/A"
    try:
        return time_obj.strftime(fmt)
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to format time object '{time_obj}' with format '{fmt}': {e}")
        return "N/A"


def combine_date_time_tz(
    date_part: date, time_part: time, tz_name: Optional[str] = None
) -> Optional[datetime]:
    """
    Combines date and time parts into a timezone-aware datetime object.

    Args:
        date_part (date): The date component.
        time_part (time): The time component.
        tz_name (Optional[str]): The target IANA timezone name. Defaults to UTC.

    Returns:
        Optional[datetime]: A timezone-aware datetime object, or None if inputs are invalid.
    """
    if not isinstance(date_part, date) or not isinstance(time_part, time):
        logger.error(f"Invalid input types for combine_date_time_tz: Date={type(date_part)}, Time={type(time_part)}")
        return None
    try:
        tz = get_timezone(tz_name)
        naive_dt = datetime.combine(date_part, time_part)
        if PYTZ_AVAILABLE and hasattr(tz, "localize"):
            aware_dt = tz.localize(naive_dt)
        else:
            aware_dt = naive_dt.replace(tzinfo=tz)
            if tz != timezone.utc:
                logger.warning("Using standard library timezone. DST handling might be incorrect for non-UTC timezones.")
        return aware_dt
    except Exception as e:
        logger.error(f"Error combining date/time/tz ({date_part}, {time_part}, {tz_name}): {e}", exc_info=True)
        return None


def calculate_end_time(start_time: time, duration: timedelta) -> Optional[time]:
    """
    Calculates the end time given a start time and duration.

    Handles wrapping around midnight correctly.

    Args:
        start_time (time): The starting time object.
        duration (timedelta): The duration as a timedelta object.

    Returns:
        Optional[time]: The resulting end time object, or None if inputs are invalid.
    """
    if not isinstance(start_time, time) or not isinstance(duration, timedelta):
        logger.error(f"Invalid input types for calculate_end_time: Start={type(start_time)}, Duration={type(duration)}")
        return None
    try:
        ref_date = date(2000, 1, 1)
        start_dt = datetime.combine(ref_date, start_time)
        end_dt = start_dt + duration
        return end_dt.time()
    except Exception as e:
        logger.error(f"Error calculating end time for start={start_time}, duration={duration}: {e}", exc_info=True)
        return None


def format_timedelta(delta: Optional[timedelta], show_seconds: bool = False) -> str:
    """
    Formats a timedelta object into a human-readable string (e.g., "2h 30m").

    Args:
        delta (Optional[timedelta]): The timedelta object. Returns "N/A" if None.
        show_seconds (bool): Whether to include seconds in the output if non-zero
                             and duration is less than a minute. Defaults to False.

    Returns:
        str: A human-readable string representation (e.g., "1h 15m", "45m", "30s").
    """
    if delta is None:
        return "N/A"
    if not isinstance(delta, timedelta):
        logger.error(f"Invalid input type for format_timedelta: {type(delta)}. Expected timedelta.")
        return "Invalid"

    total_seconds = int(delta.total_seconds())
    sign = "-" if total_seconds < 0 else ""
    total_seconds = abs(total_seconds)

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if not parts and show_seconds and seconds > 0:
        parts.append(f"{seconds}s")
    if not parts and total_seconds == 0:
        return "0m"
    if not parts:
        return f"{sign}<1m" if total_seconds > 0 else "0m"
    return sign + " ".join(parts)


def parse_duration_string(duration_str: Optional[str]) -> Optional[timedelta]:
    """
    Parses a duration string (e.g., "1h 30m", "45m", "2h", "90") into a timedelta.

    Assumes numbers without units are minutes. Handles hours (h) and minutes (m).
    Ignores seconds (s) for simplicity, logs warning if present.

    Args:
        duration_str (Optional[str]): The string representation of the duration.

    Returns:
        Optional[timedelta]: A timedelta object if parsing is successful, otherwise None.
    """
    if not isinstance(duration_str, str) or not duration_str.strip():
        return None

    total_minutes = 0.0
    duration_str_processed = duration_str.lower().strip()
    pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(h|m|s)?")
    matches = pattern.findall(duration_str_processed)

    if not matches:
        try:
            total_minutes = float(duration_str_processed)
            logger.debug(f"Parsed duration string '{duration_str}' as {total_minutes} minutes (interpreted as plain number).")
        except ValueError:
            logger.error(f"Failed to parse duration string '{duration_str}': Invalid format.")
            return None
    else:
        try:
            processed_string_parts = ""
            for value_str, unit in matches:
                value = float(value_str)
                processed_string_parts += value_str + (unit or "")
                if unit == "h":
                    total_minutes += value * 60
                elif unit == "m":
                    total_minutes += value
                elif unit == "s":
                    logger.warning(
                        f"Seconds ('s') unit found in duration string '{duration_str}'. Ignoring seconds for timedelta calculation."
                    )
                elif unit == "":
                    total_minutes += value
            if len(processed_string_parts.replace(" ", "")) != len(duration_str_processed.replace(" ", "")):
                is_just_number = False
                try:
                    float(duration_str_processed)
                    is_just_number = True
                except ValueError:
                    pass
                if not is_just_number:
                    logger.error(f"Failed to parse duration string '{duration_str}': Contains unrecognized parts.")
                    return None
        except (ValueError, TypeError) as e:
            logger.error(f"Error processing matches for duration string '{duration_str}': {e}")
            return None

    try:
        total_minutes_rounded = round(total_minutes)
        if total_minutes_rounded < 0:
            logger.error(f"Parsed duration resulted in negative minutes: {total_minutes_rounded}. Returning None.")
            return None
        return timedelta(minutes=total_minutes_rounded)
    except Exception as e:
        logger.error(f"Failed to create timedelta from parsed minutes ({total_minutes}) for duration '{duration_str}': {e}")
        return None


def time_to_total_minutes(time_obj: Optional[time]) -> Optional[int]:
    """
    Converts a datetime.time object to the total number of minutes since midnight (00:00).

    Args:
        time_obj (Optional[time]): The time object.

    Returns:
        Optional[int]: Total minutes from midnight (0 to 1439), or None if input is invalid.
    """
    if not isinstance(time_obj, time):
        return None
    return time_obj.hour * 60 + time_obj.minute


def total_minutes_to_time(total_minutes: Optional[Union[int, float]]) -> Optional[time]:
    """
    Converts total minutes since midnight back to a datetime.time object.

    Handles values up to 1440 (representing 24:00 or 00:00 of next day),
    returning time(0, 0) for 1440. Clamps input to 0-1440.

    Args:
        total_minutes (Optional[Union[int, float]]): The total number of minutes (0 to 1440).
                                                     Floats are rounded.

    Returns:
        Optional[time]: The corresponding time object, or None if input is invalid.
    """
    if total_minutes is None:
        return None
    try:
        total_minutes_int = round(float(total_minutes))
        total_minutes_clamped = max(0, min(1440, total_minutes_int))
        if total_minutes_clamped != total_minutes_int:
            logger.warning(f"Input total_minutes {total_minutes_int} was outside range [0, 1440]. Clamped to {total_minutes_clamped}.")
        if total_minutes_clamped == 1440:
            return time(0, 0)
        hours, minutes = divmod(total_minutes_clamped, 60)
        return time(hour=hours, minute=minutes)
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid input for total_minutes_to_time: {total_minutes}. Error: {e}")
        return None


# --- Example Usage ---
async def run_example():
    """Runs examples demonstrating time utility functions."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("--- Running time_utils Example ---")

    # Timezone examples
    print("\n--- Timezone Examples ---")
    utc_tz = get_timezone("UTC")
    warsaw_tz = get_timezone("Europe/Warsaw")
    invalid_tz = get_timezone("Invalid/Zone")
    print(f"UTC TZ: {utc_tz}")
    print(f"Warsaw TZ: {warsaw_tz}")
    print(f"Invalid TZ -> UTC: {invalid_tz}")
    print(f"Current time UTC: {get_current_time_in_tz('UTC')}")
    print(f"Current time Warsaw: {get_current_time_in_tz('Europe/Warsaw')}")

    # Parsing/Formatting examples
    print("\n--- Parsing/Formatting Examples ---")
    t1 = parse_time_string("16:05")
    t2 = parse_time_string("08:30:15", "%H:%M:%S")
    t_invalid = parse_time_string("25:00")
    print(f"Parsed '16:05': {t1}")
    print(f"Parsed '08:30:15': {t2}")
    print(f"Parsed '25:00': {t_invalid}")
    print(f"Formatted t1 ('%I:%M %p'): {format_time_object(t1, '%I:%M %p')}")
    print(f"Formatted t2 ('%H%M'): {format_time_object(t2, '%H%M')}")

    # Combine example
    print("\n--- Combine Date/Time/TZ Example ---")
    d = date(2024, 5, 15)
    aware_dt = combine_date_time_tz(d, t1, "America/New_York")
    print(f"Combined DT (NY): {aware_dt}")

    # Calculation examples
    print("\n--- Calculation Examples ---")
    start = time(23, 15)
    duration = timedelta(hours=2, minutes=30)
    end = calculate_end_time(start, duration)
    print(f"Start: {format_time_object(start)}, Duration: {format_timedelta(duration)}, End: {format_time_object(end)}")

    # Duration parsing examples
    print("\n--- Duration Parsing Examples ---")
    durations_to_parse = ["2h 15m", "75m", "1h", "30", "1.5h", "45s", "1h 5m 30s", "invalid"]
    for dur_str in durations_to_parse:
        parsed_delta = parse_duration_string(dur_str)
        formatted = format_timedelta(parsed_delta) if parsed_delta is not None else "Parse Failed"
        print(f"Parsed '{dur_str}': {parsed_delta} -> Formatted: '{formatted}'")

    # Minutes conversion examples
    print("\n--- Minutes Conversion Examples ---")
    minutes1 = time_to_total_minutes(time(14, 55))
    minutes2 = time_to_total_minutes(time(0, 5))
    print(f"Minutes for 14:55: {minutes1}")
    print(f"Minutes for 00:05: {minutes2}")
    time1 = total_minutes_to_time(minutes1)
    time2 = total_minutes_to_time(90)  # 1h 30m
    time3 = total_minutes_to_time(1440)  # Midnight/End of day
    time4 = total_minutes_to_time(-10)  # Invalid input gets clamped to 0
    print(f"Time from {minutes1} min: {format_time_object(time1)}")
    print(f"Time from 90 min: {format_time_object(time2)}")
    print(f"Time from 1440 min: {format_time_object(time3)}")
    print(f"Time from -10 min: {format_time_object(time4)}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_example())
