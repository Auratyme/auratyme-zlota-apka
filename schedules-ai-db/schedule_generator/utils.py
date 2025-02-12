# utils.py

from datetime import time


def find_time_interval(current_time: time) -> str:
    """
    Finds the corresponding time interval string for a given time.

    :param current_time: Time object representing the current time.
    :return: String representing the time interval.
    """
    hour = current_time.hour
    minute = current_time.minute
    start_minute = (minute // 10) * 10
    end_minute = start_minute + 9
    if end_minute >= 60:
        end_minute = 59
    return f"From {hour:02d}:{start_minute:02d} to {hour:02d}:{end_minute:02d}"


def map_activity_to_column(activity: str) -> str:
    """
    Maps activity names to corresponding column names in schedule_dataset_males_2010 dataset.

    :param activity: Activity name.
    :return: Corresponding column name.
    """
    mapping = {
        'Personal care except eating': 'Personal care except eating',
        'Eating': 'Eating',
        'Work and study': 'Work and study',
        'Household and family care and related travel': 'Household and family care and related travel',
        'Leisure. social and associative life except TV and video': 'Leisure. social and associative life except TV and video',
        'Television and video': 'Television and video',
        'Travel to/from work/study': 'Travel to/from work/study',
        'Unspecified time use and travel': 'Unspecified time use and travel'
    }
    return mapping.get(activity, activity)
