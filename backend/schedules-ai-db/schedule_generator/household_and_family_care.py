# household_and_family_care.py

from datetime import datetime, timedelta
from typing import List, Dict
from config import Config
from utils import split_activity_across_midnight, round_time_to_nearest_minutes
import logging

class HouseholdAndFamilyCareScheduler:
    """
    Handles scheduling of household and family care activities.
    """

    def __init__(self, profile: Dict):
        self.profile = profile
        self.date_str = profile['Date']
        self.person_id = profile['Person_ID']

    def schedule_household_activities(self, current_time: datetime, schedule: List[Dict]) -> datetime:
        """
        Schedules household and family care activities.

        Args:
            current_time (datetime): The current time in the schedule.
            schedule (List[Dict]): The schedule to append activities to.

        Returns:
            datetime: The updated current time after scheduling activities.
        """
        activities = ['Cleaning', 'Cooking', 'Laundry']
        for activity in activities:
            preferred_time = self.get_preferred_time(activity)
            if preferred_time:
                start_time_str, end_time_str = preferred_time
                try:
                    start_time = datetime.strptime(f"{self.date_str} {start_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
                    end_time = datetime.strptime(f"{self.date_str} {end_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
                except ValueError as e:
                    logging.error(f"Invalid preferred times for {activity} for Person_ID {self.person_id}: {e}. Skipping.")
                    continue

                # If start_time is before current_time, set start_time to current_time
                if start_time < current_time:
                    start_time = current_time

                duration = self.get_activity_duration(activity)
                activity_end_time = start_time + timedelta(minutes=duration)

                # Round times to the nearest 5 minutes
                start_time = round_time_to_nearest_minutes(start_time, base=5)
                activity_end_time = round_time_to_nearest_minutes(activity_end_time, base=5)

                # Ensure activity does not exceed preferred end time
                if activity_end_time > end_time:
                    activity_end_time = end_time
                    duration = int((activity_end_time - start_time).total_seconds() / 60)
                    if duration <= 0:
                        logging.warning(f"{activity} duration for Person_ID {self.person_id} is non-positive after adjustment.")
                        continue

                # Check if activity fits in available time
                if activity_end_time > start_time:
                    activity_blocks = split_activity_across_midnight(
                        category="Household and family care and related travel",
                        start_time=start_time,
                        end_time=activity_end_time,
                        sub_activity=activity,
                        person_id=self.person_id
                    )
                    schedule.extend(activity_blocks)
                    logging.info(f"Scheduled {activity} from {start_time.strftime(Config.TIME_FORMAT)} to {activity_end_time.strftime(Config.TIME_FORMAT)} for Person_ID {self.person_id}.")
                    current_time = activity_end_time
        return current_time

    def get_preferred_time(self, activity: str) -> tuple:
        """
        Returns preferred time range for an activity.

        Args:
            activity (str): The activity name.

        Returns:
            tuple: (start_time_str, end_time_str)
        """
        preferred_times = {
            'Cleaning': ("09:00", "12:00"),
            'Cooking': ("17:00", "20:00"),
            'Laundry': ("09:00", "12:00")
        }
        return preferred_times.get(activity, None)

    def get_activity_duration(self, activity: str) -> int:
        """
        Returns typical duration for an activity.

        Args:
            activity (str): The activity name.

        Returns:
            int: Duration in minutes.
        """
        duration_ranges = {
            'Cleaning': 60,
            'Cooking': 45,
            'Laundry': 90
        }
        return duration_ranges.get(activity, 30)  # Default duration
