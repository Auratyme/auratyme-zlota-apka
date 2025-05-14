# aggregator.py

"""
Module for aggregating and comparing generated schedules with schedule_dataset_males_2010 data.
"""

import pandas as pd
import numpy as np
from typing import Tuple
from config import Config
from utils import find_time_interval
from datetime import datetime, timedelta


class Aggregator:
    """
    Aggregates generated schedules and compares them with schedule_dataset_males_2010 data.
    """

    def __init__(self, activity_data: pd.DataFrame):
        """
        Initializes the Aggregator with activity data from schedule_dataset_males_2010.

        :param activity_data: DataFrame containing schedule activity percentages.
        """
        self.activity_data = activity_data
        self.activity_data.columns = self.activity_data.columns.str.strip()

        self.column_mapping = {
            'Personal care except eating': 'Personal care except eating',
            'Eating': 'Eating',
            'Work and study': 'Work and study',
            'Household and family care and related travel': 'Household and family care and related travel',
            'Leisure. social and associative life except TV and video': 'Leisure. social and associative life except TV and video',
            'Television and video': 'Television and video',
            'Travel to/from work/study': 'Travel to/from work/study',
            'Unspecified time use and travel': 'Unspecified time use and travel'
        }

    def aggregate_schedules(self, schedules_df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregates total durations and calculates percentage distribution of activities.

        :param schedules_df: DataFrame containing generated schedules.
        :return: DataFrame with aggregated percentages for each activity.
        """
        total_durations = schedules_df.groupby('Activity')['Duration'].sum()
        total_time = schedules_df['Duration'].sum()
        activity_percentages = (total_durations / total_time) * 100

        if 'Time_Interval' in self.activity_data.columns:
            if 'Total (24 hours)' in self.activity_data['Time_Interval'].values:
                data_totals = self.activity_data[
                    self.activity_data['Time_Interval'] == 'Total (24 hours)'
                ].iloc[0]
                data_percentages = {}
                for activity in total_durations.index:
                    col_name = self._map_activity_to_column(activity)
                    if col_name in data_totals:
                        data_percentages[activity] = data_totals.get(col_name, 0)
                    else:
                        print(
                            f"Uwaga: Kolumna '{col_name}' nie istnieje w danych aktywności. Przypisuję 0."
                        )
                        data_percentages[activity] = 0

                comparison_df = pd.DataFrame(
                    {
                        'Generated_Percent': activity_percentages,
                        'Dataset_Percent': list(data_percentages.values())
                    },
                    index=activity_percentages.index
                )
                comparison_df['Difference'] = comparison_df['Generated_Percent'] - comparison_df['Dataset_Percent']
                return comparison_df
            else:
                print(
                    "Informacja: Brak wiersza 'Total (24 hours)' w kolumnie 'Time_Interval'. Przechodzę do agregacji bez porównań."
                )
        else:
            print(
                "Informacja: Brak kolumny 'Time_Interval' w danych aktywności. Przechodzę do agregacji bez porównań."
            )

        comparison_df = pd.DataFrame(
            {
                'Generated_Percent': activity_percentages
            },
            index=activity_percentages.index
        )

        return comparison_df

    def compare_schedules_with_dataset(self, schedules_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compares generated schedules with schedule_dataset_males_2010 data on a per time interval basis.
        """
        if 'Time_Interval' not in self.activity_data.columns:
            print(
                "Informacja: Kolumna 'Time_Interval' nie istnieje w danych aktywności. Pomijam szczegółowe porównanie na podstawie przedziałów czasowych."
            )
            return pd.DataFrame()

        time_intervals = self.activity_data['Time_Interval'].unique()
        all_dates = schedules_df['Date'].unique()
        interval_df = pd.DataFrame(
            [(date, interval) for date in all_dates for interval in time_intervals],
            columns=['Date', 'Time_Interval']
        )

        expanded_schedules = []
        for _, row in schedules_df.iterrows():
            start_time = datetime.strptime(row['Start_Time'], Config.TIME_FORMAT)
            end_time = datetime.strptime(row['End_Time'], Config.TIME_FORMAT)
            if end_time < start_time:
                end_time += timedelta(days=1)
            duration_minutes = int((end_time - start_time).total_seconds() / 60)
            num_intervals = int(np.ceil(duration_minutes / 10))
            for i in range(num_intervals):
                interval_start = start_time + timedelta(minutes=i * 10)
                interval_end = interval_start + timedelta(minutes=10)
                if interval_end > end_time:
                    interval_end = end_time
                interval_duration = int((interval_end - interval_start).total_seconds() / 60)
                if interval_duration > 0:
                    interval_label = find_time_interval(interval_start.time())
                    expanded_schedules.append({
                        'Date': row['Date'],
                        'Time_Interval': interval_label,
                        'Activity': row['Activity'],
                        'Duration': interval_duration
                    })

        expanded_df = pd.DataFrame(expanded_schedules)
        grouped = expanded_df.groupby(['Time_Interval', 'Activity'])['Duration'].sum().reset_index()
        grouped['Total_Duration'] = grouped.groupby('Time_Interval')['Duration'].transform('sum')
        grouped['Generated_Percent'] = (grouped['Duration'] / (len(all_dates) * 10)) * 100

        available_columns = self.activity_data.columns.drop('Time_Interval').tolist()
        dataset_long = self.activity_data.melt(
            id_vars=['Time_Interval'],
            value_vars=available_columns,
            var_name='Activity_Column',
            value_name='Dataset_Percent'
        )

        dataset_long['Activity'] = dataset_long['Activity_Column'].map(self.column_mapping)
        merged_df = pd.merge(
            dataset_long,
            grouped,
            how='left',
            left_on=['Time_Interval', 'Activity'],
            right_on=['Time_Interval', 'Activity']
        )
        merged_df['Generated_Percent'] = merged_df['Generated_Percent'].fillna(0)
        merged_df['Difference'] = merged_df['Generated_Percent'] - merged_df['Dataset_Percent']
        final_df = merged_df[
            ['Time_Interval', 'Activity', 'Dataset_Percent', 'Generated_Percent', 'Difference']
        ]

        return final_df

    def _map_activity_to_column(self, activity: str) -> str:
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
        return mapping.get(activity, activity.replace(' ', '_'))
