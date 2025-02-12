# config.py

import os


class Config:
    """
    Configuration class containing paths and settings for the schedule generator.
    """

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')

    SCHEDULE_DATASET_PATH = os.path.join(DATA_DIR, 'schedule_dataset_males_2010.csv')
    ACTIVITIES_FILE = 'activities.json'
    SUB_ACTIVITIES_FILE = 'sub_activities.json'
    ACTIVITIES_PATH = os.path.join(DATA_DIR, ACTIVITIES_FILE)
    SUB_ACTIVITIES_PATH = os.path.join(DATA_DIR, SUB_ACTIVITIES_FILE)

    OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

    TIME_FORMAT = "%H:%M"
    DATE_FORMAT = "%Y-%m-%d"

    START_DATE = "2023-01-01"

    NUM_SCHEDULES = 1000
