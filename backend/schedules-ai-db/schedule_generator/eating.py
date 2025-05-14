# eating.py

from datetime import datetime, timedelta
from typing import List, Dict
from config import Config
from utils import split_activity_across_midnight, round_time_to_nearest_minutes
import logging

class EatingScheduler:
    """
    Handles scheduling of eating activities, such as breakfast, lunch, and dinner.
    """

    def __init__(self, profile: Dict):
        self.profile = profile
        self.date_str = profile['Date']
        self.person_id = profile['Person_ID']

    def schedule_breakfast(self, current_time: datetime, schedule: List[Dict]) -> datetime:
        """
        Schedules breakfast.

        Args:
            current_time (datetime): The current time in the schedule.
            schedule (List[Dict]): The schedule to append activities to.

        Returns:
            datetime: The updated current time after scheduling breakfast.
        """
        meal_time_str = self.profile.get('Preferred_Meal_Times', {}).get('breakfast')
        if meal_time_str:
            try:
                meal_time = datetime.strptime(f"{self.date_str} {meal_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
            except ValueError as e:
                logging.error(f"Invalid breakfast time for Person_ID {self.person_id}: {e}. Skipping breakfast.")
                return current_time

            # Set start_time to max(current_time, meal_time)
            start_time = max(current_time, meal_time)

            duration = self.get_meal_duration('breakfast')
            end_time = start_time + timedelta(minutes=duration)

            # Round times to the nearest 5 minutes
            start_time = round_time_to_nearest_minutes(start_time, base=5)
            end_time = round_time_to_nearest_minutes(end_time, base=5)

            # Ensure meal does not exceed work start time
            work_start_time_str = self.profile.get('Preferred_Work_Start_Time')
            if work_start_time_str and self.profile.get('Preferred_Work_Duration', 0) > 0:
                try:
                    work_start_time = datetime.strptime(f"{self.date_str} {work_start_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
                    work_duration = self.profile.get('Preferred_Work_Duration', 0)
                    work_end_time = work_start_time + timedelta(minutes=work_duration)
                    if end_time > work_start_time:
                        end_time = work_start_time
                        duration = int((end_time - start_time).total_seconds() / 60)
                        if duration <= 0:
                            logging.warning(f"Breakfast duration for Person_ID {self.person_id} is non-positive after adjustment.")
                            return current_time
                except ValueError as e:
                    logging.error(f"Invalid Preferred_Work_Start_Time for Person_ID {self.person_id}: {e}. Skipping breakfast.")
                    return current_time

            activity_blocks = split_activity_across_midnight(
                category="Eating",
                start_time=start_time,
                end_time=end_time,
                sub_activity="Breakfast",
                person_id=self.person_id
            )
            schedule.extend(activity_blocks)
            logging.info(f"Scheduled Breakfast from {start_time.strftime(Config.TIME_FORMAT)} to {end_time.strftime(Config.TIME_FORMAT)} for Person_ID {self.person_id}.")
            return end_time
        return current_time

    def schedule_lunch(self, current_time: datetime, schedule: List[Dict]) -> datetime:
        """
        Schedules lunch.

        Args:
            current_time (datetime): The current time in the schedule.
            schedule (List[Dict]): The schedule to append activities to.

        Returns:
            datetime: The updated current time after scheduling lunch.
        """
        meal_time_str = self.profile.get('Preferred_Meal_Times', {}).get('lunch')
        if meal_time_str:
            try:
                meal_time = datetime.strptime(f"{self.date_str} {meal_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
            except ValueError as e:
                logging.error(f"Invalid lunch time for Person_ID {self.person_id}: {e}. Skipping lunch.")
                return current_time

            # Set start_time to max(current_time, meal_time)
            start_time = max(current_time, meal_time)

            duration = self.get_meal_duration('lunch')
            end_time = start_time + timedelta(minutes=duration)

            # Round times to the nearest 5 minutes
            start_time = round_time_to_nearest_minutes(start_time, base=5)
            end_time = round_time_to_nearest_minutes(end_time, base=5)

            # Calculate work end time based on work start time and duration
            work_start_time_str = self.profile.get('Preferred_Work_Start_Time')
            work_duration = self.profile.get('Preferred_Work_Duration', 0)
            if work_start_time_str and work_duration > 0:
                try:
                    work_start_time = datetime.strptime(f"{self.date_str} {work_start_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
                    work_end_time = work_start_time + timedelta(minutes=work_duration)
                except ValueError as e:
                    logging.error(f"Invalid Preferred_Work_Start_Time for Person_ID {self.person_id}: {e}. Skipping lunch.")
                    return current_time

                # Ensure meal does not exceed work start time
                if end_time > work_start_time:
                    end_time = work_start_time
                    duration = int((end_time - start_time).total_seconds() / 60)
                    if duration <= 0:
                        logging.warning(f"Lunch duration for Person_ID {self.person_id} is non-positive after adjustment.")
                        return current_time

            # Ensure meal does not exceed evening routine start time
            evening_routine_duration = self.profile.get('Evening_Routine_Duration', 30)
            typical_bed_time_str = self.profile.get('Typical_Bed_Time', '22:00')
            try:
                bed_time = datetime.strptime(f"{self.date_str} {typical_bed_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
                evening_start_time = bed_time - timedelta(minutes=evening_routine_duration)
                if end_time > evening_start_time:
                    end_time = evening_start_time
                    duration = int((end_time - start_time).total_seconds() / 60)
                    if duration <= 0:
                        logging.warning(f"Lunch duration for Person_ID {self.person_id} is non-positive after adjustment.")
                        return current_time
            except ValueError as e:
                logging.error(f"Invalid Typical_Bed_Time for Person_ID {self.person_id}: {e}. Skipping lunch.")
                return current_time

            activity_blocks = split_activity_across_midnight(
                category="Eating",
                start_time=start_time,
                end_time=end_time,
                sub_activity="Lunch",
                person_id=self.person_id
            )
            schedule.extend(activity_blocks)
            logging.info(f"Scheduled Lunch from {start_time.strftime(Config.TIME_FORMAT)} to {end_time.strftime(Config.TIME_FORMAT)} for Person_ID {self.person_id}.")
            return end_time
        return current_time

    def schedule_dinner(self, current_time: datetime, schedule: List[Dict]) -> datetime:
        """
        Schedules dinner.

        Args:
            current_time (datetime): The current time in the schedule.
            schedule (List[Dict]): The schedule to append activities to.

        Returns:
            datetime: The updated current time after scheduling dinner.
        """
        meal_time_str = self.profile.get('Preferred_Meal_Times', {}).get('dinner')
        if meal_time_str:
            try:
                meal_time = datetime.strptime(f"{self.date_str} {meal_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
            except ValueError as e:
                logging.error(f"Invalid dinner time for Person_ID {self.person_id}: {e}. Skipping dinner.")
                return current_time

            # Set start_time to max(current_time, meal_time)
            start_time = max(current_time, meal_time)

            duration = self.get_meal_duration('dinner')
            end_time = start_time + timedelta(minutes=duration)

            # Round times to the nearest 5 minutes
            start_time = round_time_to_nearest_minutes(start_time, base=5)
            end_time = round_time_to_nearest_minutes(end_time, base=5)

            # Ensure meal does not exceed evening routine start time
            evening_routine_duration = self.profile.get('Evening_Routine_Duration', 30)
            typical_bed_time_str = self.profile.get('Typical_Bed_Time', '22:30')
            try:
                bed_time = datetime.strptime(f"{self.date_str} {typical_bed_time_str}", f"{Config.DATE_FORMAT} {Config.TIME_FORMAT}")
                evening_start_time = bed_time - timedelta(minutes=evening_routine_duration)
                if end_time > evening_start_time:
                    end_time = evening_start_time
                    duration = int((end_time - start_time).total_seconds() / 60)
                    if duration <= 0:
                        logging.warning(f"Dinner duration for Person_ID {self.person_id} is non-positive after adjustment.")
                        return current_time
            except ValueError as e:
                logging.error(f"Invalid Typical_Bed_Time for Person_ID {self.person_id}: {e}. Skipping dinner.")
                return current_time

            activity_blocks = split_activity_across_midnight(
                category="Eating",
                start_time=start_time,
                end_time=end_time,
                sub_activity="Dinner",
                person_id=self.person_id
            )
            schedule.extend(activity_blocks)
            logging.info(f"Scheduled Dinner from {start_time.strftime(Config.TIME_FORMAT)} to {end_time.strftime(Config.TIME_FORMAT)} for Person_ID {self.person_id}.")
            return end_time
        return current_time

    def get_meal_duration(self, meal: str) -> int:
        """
        Returns the typical duration for a meal.

        Args:
            meal (str): The meal name ('breakfast', 'lunch', 'dinner').

        Returns:
            int: Duration in minutes.
        """
        meal_durations = {
            'breakfast': 30,
            'lunch': 45,
            'dinner': 60
        }
        return meal_durations.get(meal, 30)  # Default duration
