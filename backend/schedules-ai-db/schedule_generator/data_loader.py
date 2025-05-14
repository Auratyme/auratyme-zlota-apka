# data_loader.py

import pandas as pd
import json
import random
from typing import Dict, List
from config import Config

class DataLoader:
    """
    Loads schedule data and activity categories from CSV and JSON files.
    """
    
    def __init__(self):
        """
        Initializes the DataLoader with paths to necessary files.
        """
        self.schedule_dataset_path = Config.SCHEDULE_DATASET_PATH
        self.activities_path = Config.ACTIVITIES_PATH
        self.sub_activities_path = Config.SUB_ACTIVITIES_PATH

    def load_schedule_data(self) -> pd.DataFrame:
        """
        Loads the schedule dataset from a CSV file.
    
        :return: DataFrame containing schedule activity percentages.
        """
        df = pd.read_csv(self.schedule_dataset_path)
        
        if 'ACL00 (Labels)' in df.columns:
            df.rename(columns={'ACL00 (Labels)': 'Time_Interval'}, inplace=True)
        else:
            print("Kolumna 'Time_Interval' już istnieje lub brak kolumny 'ACL00 (Labels)'.")
        
        return df

    def load_activity_categories(self) -> 'ActivityCategories':
        """
        Loads the activity categories from JSON files.
    
        :return: Instance of ActivityCategories containing categories and sub-activities.
        """
        with open(self.activities_path, 'r', encoding='utf-8') as f:
            activities = json.load(f)
        
        with open(self.sub_activities_path, 'r', encoding='utf-8') as f:
            sub_activities = json.load(f)
        
        return ActivityCategories(activities, sub_activities)

class ActivityCategories:
    """
    Manages activity categories and their sub-activities.
    """
    
    def __init__(self, activities: Dict[str, float], sub_activities: Dict[str, List[str]]):
        """
        Initializes the ActivityCategories with activities and sub-activities.
    
        :param activities: Dictionary of activities with their corresponding percentages.
        :param sub_activities: Dictionary mapping activities to their sub-activities.
        """
        self.activities = activities
        self.sub_activities = sub_activities

    def get_categories(self) -> List[str]:
        """
        Returns the list of main activity categories.
    
        :return: List of activity category names.
        """
        return list(self.activities.keys())

    def get_percentage(self, category: str) -> float:
        """
        Returns the percentage of a given activity category.
    
        :param category: Name of the activity category.
        :return: Percentage of the activity.
        """
        return self.activities.get(category, 0.0)

    def get_random_activity(self, category: str) -> str:
        """
        Returns a random sub-activity for a given category.
    
        :param category: Name of the activity category.
        :return: Name of the sub-activity.
        """
        sub_acts = self.sub_activities.get(category, [])
        if not sub_acts:
            raise ValueError(f"Kategoria aktywności '{category}' nie ma przypisanych sub-aktywności.")
        return random.choice(sub_acts)
