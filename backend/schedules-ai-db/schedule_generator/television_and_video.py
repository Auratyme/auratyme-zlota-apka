# television_and_video.py

from datetime import datetime, timedelta
from typing import List, Dict
from utils import split_activity_across_midnight, round_time_to_nearest_minutes
import random
import logging
from config import Config

class TelevisionAndVideo:
    """
    Handles the scheduling of 'Television and video' activities.
    """

    def __init__(self, profile: Dict):
        """
        Initializes the scheduler with the user's profile.

        Args:
            profile (Dict): Profile dictionary containing user preferences and information.
        """
        self.profile = profile
        self.date_str = profile['Date']
        self.person_id = profile['Person_ID']

    def generate_television_time(self, current_time: datetime, is_weekend: bool) -> List[Dict]:
        """
        Generates television and video activities starting exactly at current_time.

        Args:
            current_time (datetime): The current time in the schedule.
            is_weekend (bool): Indicates if the day is a weekend.

        Returns:
            List[Dict]: List of activity blocks for television and video.
        """
        available_minutes = self.calculate_available_minutes(current_time)
        if available_minutes <= 0:
            return []

        # Decide duration based on whether it's a weekend or not
        if is_weekend:
            tv_duration = random.randint(60, 180)  # 1 to 3 hours
        else:
            tv_duration = random.randint(30, 120)  # 0.5 to 2 hours

        # Ensure that duration does not exceed available time
        tv_duration = min(tv_duration, available_minutes)

        tv_end_time = current_time + timedelta(minutes=tv_duration)
        # Round times to the nearest 5 minutes
        tv_start_time = round_time_to_nearest_minutes(current_time, base=5)
        tv_end_time = round_time_to_nearest_minutes(tv_end_time, base=5)

        # Ensure tv_end_time does not exceed day end
        day_end_time = current_time.replace(hour=23, minute=59, second=0, microsecond=0)
        if tv_end_time > day_end_time:
            tv_end_time = day_end_time
            tv_duration = int((tv_end_time - tv_start_time).total_seconds() / 60)
            if tv_duration <= 0:
                logging.warning(f"Television and Video duration for Person_ID {self.person_id} is non-positive after adjustment.")
                return []

        activity_blocks = split_activity_across_midnight(
            category="Television and video",
            start_time=tv_start_time,
            end_time=tv_end_time,
            sub_activity="Watching TV",
            person_id=self.person_id
        )
        logging.info(f"Scheduled Television and Video from {tv_start_time.strftime(Config.TIME_FORMAT)} to {tv_end_time.strftime(Config.TIME_FORMAT)} for Person_ID {self.person_id}.")
        return activity_blocks

    def calculate_available_minutes(self, current_time: datetime) -> int:
        """
        Calculates the available minutes for television activities.

        Args:
            current_time (datetime): Current datetime.

        Returns:
            int: Number of available minutes.
        """
        day_end = current_time.replace(hour=23, minute=59, second=0, microsecond=0)
        remaining_minutes = int((day_end - current_time).total_seconds() / 60)
        return max(0, remaining_minutes)
