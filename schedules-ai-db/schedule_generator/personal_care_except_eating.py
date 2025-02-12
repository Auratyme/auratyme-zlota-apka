# personal_care_except_eating.py

from datetime import datetime, timedelta
from typing import List, Dict
from config import Config
from utils import split_activity_across_midnight, round_time_to_nearest_minutes
import logging

class PersonalCareScheduler:
    """
    Handles scheduling of personal care activities excluding eating.
    Includes scheduling of sleep, ensuring it is split across midnight if necessary.
    """

    def __init__(self, profile: Dict):
        self.profile = profile
        self.date_str = profile['Date']
        self.person_id = profile['Person_ID']

    def schedule_personal_care_morning(self, current_time: datetime, schedule: List[Dict]) -> datetime:
        """
        Schedules morning personal care activities.

        Args:
            current_time (datetime): The current time in the schedule.
            schedule (List[Dict]): The schedule to append activities to.

        Returns:
            datetime: The updated current time after scheduling activities.
        """
        # Morning Routine
        morning_duration = self.profile.get('Morning_Routine_Duration', 30)
        wake_up_time_str = self.profile.get('Typical_Wake_Up_Time', '07:00')
        try:
            wake_up_time = datetime.strptime(f"{self.date_str} {wake_up_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
        except ValueError as e:
            logging.error(f"Invalid Typical_Wake_Up_Time for Person_ID {self.person_id}: {e}. Using default '07:00'.")
            wake_up_time = datetime.strptime(f"{self.date_str} 07:00", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")

        # Set start_time to max(current_time, wake_up_time)
        start_time = max(current_time, wake_up_time)

        end_time = start_time + timedelta(minutes=morning_duration)

        # Round times to the nearest 5 minutes
        start_time = round_time_to_nearest_minutes(start_time, base=5)
        end_time = round_time_to_nearest_minutes(end_time, base=5)

        # Check if activity fits in available time
        if end_time > start_time:
            activity_blocks = split_activity_across_midnight(
                category="Personal care except eating",
                start_time=start_time,
                end_time=end_time,
                sub_activity="Morning Routine",
                person_id=self.person_id
            )
            schedule.extend(activity_blocks)
            logging.info(f"Scheduled Morning Routine from {start_time.strftime(Config.TIME_FORMAT)} to {end_time.strftime(Config.TIME_FORMAT)} for Person_ID {self.person_id}.")
            return end_time
        else:
            logging.warning(f"Morning Routine for Person_ID {self.person_id} has non-positive duration after rounding.")
            return current_time

    def schedule_personal_care_evening(self, current_time: datetime, schedule: List[Dict]) -> datetime:
        """
        Schedules evening personal care activities and sleep.

        Args:
            current_time (datetime): The current time in the schedule.
            schedule (List[Dict]): The schedule to append activities to.

        Returns:
            datetime: The updated current time after scheduling activities.
        """
        # Evening Routine
        evening_duration = self.profile.get('Evening_Routine_Duration', 30)
        typical_bed_time_str = self.profile.get('Typical_Bed_Time', '22:00')
        try:
            bed_time = datetime.strptime(f"{self.date_str} {typical_bed_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
        except ValueError as e:
            logging.error(f"Invalid Typical_Bed_Time for Person_ID {self.person_id}: {e}. Using default '22:00'.")
            bed_time = datetime.strptime(f"{self.date_str} 22:00", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")

        # Calculate evening routine start time
        evening_start_time = bed_time - timedelta(minutes=evening_duration)

        # Set start_time to max(current_time, evening_start_time)
        start_time = max(current_time, evening_start_time)

        # Round times to the nearest 5 minutes
        start_time = round_time_to_nearest_minutes(start_time, base=5)
        bed_time = round_time_to_nearest_minutes(bed_time, base=5)

        # Check if activity fits in available time
        if bed_time > start_time:
            activity_blocks = split_activity_across_midnight(
                category="Personal care except eating",
                start_time=start_time,
                end_time=bed_time,
                sub_activity="Evening Routine",
                person_id=self.person_id
            )
            schedule.extend(activity_blocks)
            logging.info(f"Scheduled Evening Routine from {start_time.strftime(Config.TIME_FORMAT)} to {bed_time.strftime(Config.TIME_FORMAT)} for Person_ID {self.person_id}.")
        else:
            logging.warning(f"Evening Routine for Person_ID {self.person_id} has non-positive duration after rounding.")
            bed_time = current_time

        # Schedule Sleep
        sleep_start_time = bed_time
        wake_up_time_str = self.profile.get('Typical_Wake_Up_Time', '07:00')
        try:
            wake_up_time = datetime.strptime(f"{self.date_str} {wake_up_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
        except ValueError as e:
            logging.error(f"Invalid Typical_Wake_Up_Time for Person_ID {self.person_id}: {e}. Using default '07:00'.")
            wake_up_time = datetime.strptime(f"{self.date_str} 07:00", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")

        # If wake_up_time is earlier than sleep_start_time, it means sleep crosses midnight
        if wake_up_time <= sleep_start_time:
            wake_up_time += timedelta(days=1)

        sleep_end_time = wake_up_time

        # Round times to the nearest 5 minutes
        sleep_start_time = round_time_to_nearest_minutes(sleep_start_time, base=5)
        sleep_end_time = round_time_to_nearest_minutes(sleep_end_time, base=5)

        # Check if sleep duration is positive
        if sleep_end_time > sleep_start_time:
            activity_blocks = split_activity_across_midnight(
                category="Personal care except eating",
                start_time=sleep_start_time,
                end_time=sleep_end_time,
                sub_activity="Sleep",
                person_id=self.person_id
            )
            schedule.extend(activity_blocks)
            logging.info(f"Scheduled Sleep from {sleep_start_time.strftime(Config.TIME_FORMAT)} to {sleep_end_time.strftime(Config.TIME_FORMAT)} for Person_ID {self.person_id}.")
            return sleep_end_time
        else:
            logging.warning(f"Sleep duration for Person_ID {self.person_id} is non-positive after rounding.")
            return sleep_start_time
