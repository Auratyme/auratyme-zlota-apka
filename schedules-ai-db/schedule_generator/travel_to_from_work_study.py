# travel_to_from_work_study.py

from datetime import datetime, timedelta
from typing import List, Dict
from utils import split_activity_across_midnight, round_time_to_nearest_minutes
import random
import logging
from config import Config

class TravelToFromWorkStudy:
    """
    Handles the scheduling of 'Travel to/from work/study' activities.
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

    def generate_commute_to(self, current_time: datetime, is_weekend: bool) -> List[Dict]:
        """
        Generates commute to work or study activities starting exactly at current_time.

        Args:
            current_time (datetime): The current time in the schedule.
            is_weekend (bool): Indicates if the day is a weekend.

        Returns:
            List[Dict]: List of activity blocks for commuting to work/study.
        """
        if self.should_commute(is_weekend):
            commute_duration = self.get_commute_duration()
            commute_end_time = current_time + timedelta(minutes=commute_duration)
            # Round times to the nearest 5 minutes
            commute_start_time = round_time_to_nearest_minutes(current_time, base=5)
            commute_end_time = round_time_to_nearest_minutes(commute_end_time, base=5)

            # Ensure commute does not exceed work start time
            work_start_time_str = self.profile.get('Preferred_Work_Start_Time')
            if work_start_time_str:
                try:
                    work_start_time = datetime.strptime(f"{self.date_str} {work_start_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
                    if commute_end_time > work_start_time:
                        commute_end_time = work_start_time
                        commute_duration = int((commute_end_time - commute_start_time).total_seconds() / 60)
                        if commute_duration <= 0:
                            logging.warning(f"Commute To duration for Person_ID {self.person_id} is non-positive after adjustment.")
                            return []
                except ValueError as e:
                    logging.error(f"Invalid Preferred_Work_Start_Time for Person_ID {self.person_id}: {e}. Skipping Commute To.")
                    return []

            activity_blocks = split_activity_across_midnight(
                category="Travel to/from work/study",
                start_time=commute_start_time,
                end_time=commute_end_time,
                sub_activity="Commute To",
                person_id=self.person_id
            )
            logging.info(f"Scheduled Commute To Work/Study from {commute_start_time.strftime(Config.TIME_FORMAT)} to {commute_end_time.strftime(Config.TIME_FORMAT)} for Person_ID {self.person_id}.")
            return activity_blocks
        return []

    def generate_commute_from(self, current_time: datetime, is_weekend: bool) -> List[Dict]:
        """
        Generates commute from work or study activities starting exactly at current_time.

        Args:
            current_time (datetime): The current time in the schedule.
            is_weekend (bool): Indicates if the day is a weekend.

        Returns:
            List[Dict]: List of activity blocks for commuting from work/study.
        """
        if self.should_commute(is_weekend):
            commute_duration = self.get_commute_duration()
            commute_end_time = current_time + timedelta(minutes=commute_duration)
            # Round times to the nearest 5 minutes
            commute_start_time = round_time_to_nearest_minutes(current_time, base=5)
            commute_end_time = round_time_to_nearest_minutes(commute_end_time, base=5)

            # No need to check against work_end_time as it's after work/study

            activity_blocks = split_activity_across_midnight(
                category="Travel to/from work/study",
                start_time=commute_start_time,
                end_time=commute_end_time,
                sub_activity="Commute From",
                person_id=self.person_id
            )
            logging.info(f"Scheduled Commute From Work/Study from {commute_start_time.strftime(Config.TIME_FORMAT)} to {commute_end_time.strftime(Config.TIME_FORMAT)} for Person_ID {self.person_id}.")
            return activity_blocks
        return []

    def should_commute(self, is_weekend: bool) -> bool:
        """
        Determines whether the person should commute on a given day.

        Args:
            is_weekend (bool): Indicates if the day is a weekend.

        Returns:
            bool: True if the person should commute, False otherwise.
        """
        occupation = self.profile.get('Occupation', 'Unemployed')
        if occupation in ["Unemployed", "Retired"]:
            return False
        if is_weekend and occupation != "Freelancer":
            return False
        return True

    def get_commute_duration(self) -> int:
        """
        Generates a random commute duration.

        Returns:
            int: Commute duration in minutes.
        """
        # Customize commute duration range as needed
        return random.randint(15, 60)  # 15 to 60 minutes
