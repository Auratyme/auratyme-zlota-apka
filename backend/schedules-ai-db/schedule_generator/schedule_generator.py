# schedule_generator.py

import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np
from data_loader import DataLoader
from config import Config
from utils import map_activity_to_column


class ScheduleGenerator:
    """
    Generates realistic schedules based on schedule_dataset_males_2010 activity distributions.
    """

    def __init__(self, data_loader: DataLoader):
        """
        Initializes the ScheduleGenerator with a DataLoader instance.

        :param data_loader: Instance of DataLoader containing schedule data and categories.
        """
        self.schedule_data = data_loader.load_schedule_data()
        self.schedule_data.columns = self.schedule_data.columns.str.strip()
        self.activity_categories = data_loader.load_activity_categories()

        self.activity_durations = {
            'Personal care except eating': (30, 90),
            'Personal care (Sleep)': (300, 600),
            'Eating': (15, 60),
            'Work and study': (240, 600),
            'Household and family care and related travel': (30, 180),
            'Leisure, social and associative life except TV': (30, 240),
            'Television and video': (30, 180),
            'Travel to/from work/study': (15, 120),
            'Unspecified time use and travel': (0, 60)
        }

    def generate_schedules(self, num_schedules: int) -> pd.DataFrame:
        """
        Generates schedules for a specified number of schedules based on the time-of-day activity distributions.

        :param num_schedules: Number of schedules to generate.
        :return: DataFrame containing all generated schedules.
        """
        all_schedules = {
            'Date': [],
            'Activity': [],
            'Start_Time': [],
            'End_Time': [],
            'Duration': []
        }

        start_date = datetime.strptime(Config.START_DATE, Config.DATE_FORMAT)
        dates = [start_date + timedelta(days=i) for i in range(num_schedules)]
        date_strs = [date.strftime(Config.DATE_FORMAT) for date in dates]

        time_intervals = self.schedule_data['Time_Interval'].unique()
        time_intervals = [
            interval for interval in time_intervals if interval != 'Total (24 hours)'
        ]

        activities = self.activity_categories.get_categories()
        print(f"Lista aktywności: {activities}")

        for i in range(num_schedules):
            current_date = date_strs[i]
            schedule = []
            prev_activity = None
            for interval in time_intervals:
                print(f"Przetwarzanie przedziału czasowego: {interval}")

                interval_data = self.schedule_data[
                    self.schedule_data['Time_Interval'] == interval
                ]
                if interval_data.empty:
                    print(f"Brak danych dla przedziału czasowego: {interval}")
                    continue
                interval_data = interval_data.iloc[0]

                percentages = [
                    interval_data[map_activity_to_column(act)] for act in activities
                ]
                total_percent = sum(percentages)
                if total_percent == 0:
                    norm_percentages = [1.0 / len(percentages)] * len(percentages)
                else:
                    norm_percentages = [p / total_percent for p in percentages]

                if prev_activity:
                    for idx, act in enumerate(activities):
                        if act == prev_activity:
                            norm_percentages[idx] *= 1.2
                    total_weight = sum(norm_percentages)
                    norm_percentages = [p / total_weight for p in norm_percentages]

                activity = random.choices(
                    activities, weights=norm_percentages, k=1
                )[0]
                prev_activity = activity

                schedule.append({
                    'Time_Interval': interval,
                    'Activity': activity
                })

            merged_schedule = self._merge_intervals(schedule)

            for entry in merged_schedule:
                start_time = entry['Start_Time']
                end_time = entry['End_Time']
                duration = self._calculate_duration(start_time, end_time)
                all_schedules['Date'].append(current_date)
                all_schedules['Activity'].append(entry['Activity'])
                all_schedules['Start_Time'].append(start_time)
                all_schedules['End_Time'].append(end_time)
                all_schedules['Duration'].append(duration)

        generated_df = pd.DataFrame(all_schedules)
        self.validate_schedule(generated_df)

        return generated_df

    def _merge_intervals(self, schedule: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Merges consecutive intervals with the same activity.

        :param schedule: List of schedule entries.
        :return: Merged schedule.
        """
        merged = []
        prev_activity = None
        for entry in schedule:
            time_interval = entry['Time_Interval']
            activity = entry['Activity']
            start_time_str, end_time_str = self._get_interval_times(time_interval)
            if prev_activity and activity == prev_activity['Activity']:
                prev_activity['End_Time'] = end_time_str
            else:
                prev_activity = {
                    'Activity': activity,
                    'Start_Time': start_time_str,
                    'End_Time': end_time_str
                }
                merged.append(prev_activity)
        return merged

    def _get_interval_times(self, time_interval: str) -> Tuple[str, str]:
        """
        Parses the Time_Interval string to extract start and end times.

        :param time_interval: Time interval string.
        :return: Tuple of start and end time strings.
        """
        parts = time_interval.replace('From ', '').split(' to ')
        return parts[0], parts[1]

    def _calculate_duration(self, start_time_str: str, end_time_str: str) -> int:
        """
        Calculates the duration in minutes between two time strings.

        :param start_time_str: Start time as a string.
        :param end_time_str: End time as a string.
        :return: Duration in minutes.
        """
        start_time = datetime.strptime(start_time_str, Config.TIME_FORMAT)
        end_time = datetime.strptime(end_time_str, Config.TIME_FORMAT)
        if end_time < start_time:
            end_time += timedelta(days=1)
        duration = int((end_time - start_time).total_seconds() / 60)
        return duration

    def calculate_target_durations(self, total_minutes: int = 1440) -> Dict[str, int]:
        """
        Calculates the target duration in minutes for each activity category
        based on the percentage data provided in the dataset.

        :param total_minutes: Total number of minutes in a day (24 hours by default).
        :return: A dictionary with activities as keys and target durations in minutes as values.
        """
        target_durations = {}
        for activity, percentage in self.activity_categories.activities_percentages.items():
            target_duration = int((percentage / 100) * total_minutes)
            target_durations[activity] = target_duration
        return target_durations

    def adjust_schedule_to_target(
        self, schedule_df: pd.DataFrame, target_durations: Dict[str, int]
    ) -> pd.DataFrame:
        """
        Adjusts the generated schedule to fit the target durations more closely.

        :param schedule_df: The generated schedule DataFrame with initial durations.
        :param target_durations: Dictionary of target durations in minutes for each activity.
        :return: Adjusted DataFrame with minimized differences in duration.
        """
        adjusted_schedule_df = schedule_df.copy()

        for activity, target_duration in target_durations.items():
            activity_rows = adjusted_schedule_df[adjusted_schedule_df['Activity'] == activity]
            actual_duration = activity_rows['Duration'].sum()
            duration_difference = target_duration - actual_duration

            if duration_difference != 0 and not activity_rows.empty:
                adjustment = duration_difference / len(activity_rows)
                adjusted_durations = (
                    activity_rows['Duration'] + adjustment
                ).clip(lower=1).astype(int)
                adjusted_schedule_df.loc[activity_rows.index, 'Duration'] = adjusted_durations

        adjusted_schedule_df['End_Time'] = adjusted_schedule_df.apply(
            lambda row: (
                datetime.strptime(row['Start_Time'], Config.TIME_FORMAT)
                + timedelta(minutes=row['Duration'])
            ).strftime(Config.TIME_FORMAT),
            axis=1
        )

        return adjusted_schedule_df

    def validate_schedule(self, schedules_df: pd.DataFrame):
        """
        Validates that each schedule sums up to 1440 minutes.

        :param schedules_df: DataFrame containing generated schedules.
        """
        total_minutes = schedules_df.groupby('Date')['Duration'].sum()
        invalid_schedules = total_minutes[total_minutes != 1440]
        if not invalid_schedules.empty:
            print("Następujące harmonogramy nie sumują się do 1440 minut:")
            print(invalid_schedules)
        else:
            print("Wszystkie harmonogramy są poprawne i sumują się do 1440 minut.")
