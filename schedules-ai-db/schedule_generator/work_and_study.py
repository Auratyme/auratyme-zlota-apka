# work_and_study.py

from datetime import datetime, timedelta
from typing import List, Dict
from config import Config
from utils import split_activity_across_midnight, round_time_to_nearest_minutes
import logging

class WorkAndStudyScheduler:
    """
    Handles scheduling of work and study activities.
    """

    def __init__(self, profile: Dict):
        self.profile = profile
        self.date_str = profile['Date']
        self.person_id = profile['Person_ID']

    def schedule_work_study(self, current_time: datetime, schedule: List[Dict]) -> datetime:
        """
        Schedules work or study activities within wake hours.

        Args:
            current_time (datetime): The current time in the schedule.
            schedule (List[Dict]): The schedule to append activities to.

        Returns:
            datetime: The updated current time after scheduling activities.
        """
        preferred_start_time_str = self.profile.get('Preferred_Work_Start_Time')
        work_duration = self.profile.get('Preferred_Work_Duration', 0)
        if preferred_start_time_str and work_duration > 0:
            try:
                start_time = datetime.strptime(f"{self.date_str} {preferred_start_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
            except ValueError as e:
                logging.error(f"Invalid Preferred_Work_Start_Time for Person_ID {self.person_id}: {e}. Skipping Work/Study scheduling.")
                return current_time

            # Set start_time to max(current_time, start_time)
            start_time = max(current_time, start_time)

            end_time = start_time + timedelta(minutes=work_duration)

            # Ensure work does not exceed bed time
            typical_bed_time_str = self.profile.get('Typical_Bed_Time', '22:30')
            try:
                bed_time = datetime.strptime(f"{self.date_str} {typical_bed_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
                if end_time > bed_time:
                    end_time = bed_time
                    work_duration = int((end_time - start_time).total_seconds() / 60)
                    if work_duration <= 0:
                        logging.warning(f"Work/Study duration for Person_ID {self.person_id} is non-positive after adjustment.")
                        return current_time
            except ValueError as e:
                logging.error(f"Invalid Typical_Bed_Time for Person_ID {self.person_id}: {e}. Skipping Work/Study scheduling.")
                return current_time

            # Round times to the nearest 5 minutes
            start_time = round_time_to_nearest_minutes(start_time, base=5)
            end_time = round_time_to_nearest_minutes(end_time, base=5)

            # Check if activity fits in available time
            if end_time > start_time:
                activity_blocks = split_activity_across_midnight(
                    category="Work and study",
                    start_time=start_time,
                    end_time=end_time,
                    sub_activity="Work/Study",
                    person_id=self.person_id
                )
                schedule.extend(activity_blocks)
                logging.info(f"Scheduled Work/Study from {start_time.strftime(Config.TIME_FORMAT)} to {end_time.strftime(Config.TIME_FORMAT)} for Person_ID {self.person_id}.")
                return end_time
            else:
                logging.warning(f"Work/Study for Person_ID {self.person_id} has non-positive duration after rounding.")
                return current_time
        else:
            # Person does not have work/study obligations
            logging.info(f"Person_ID {self.person_id} does not have Work/Study activities.")
            return current_time
