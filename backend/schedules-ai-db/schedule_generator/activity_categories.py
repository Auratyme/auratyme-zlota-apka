# activity_categories.py

import json
import os
import numpy as np
from typing import List, Dict
from config import Config


class ActivityCategory:
    """
    Represents a category of activity with a name and a list of possible activities.
    """

    def __init__(self, name: str, activities: List[str]):
        """
        Initializes the ActivityCategory with a name and a list of activities.

        :param name: Name of the activity category.
        :param activities: List of possible activities within the category.
        """
        self.name = name
        self.activities = activities


class ActivityCategories:
    """
    Manages multiple activity categories, including their percentages and sub-activities.
    """

    def __init__(self):
        """
        Initializes the ActivityCategories by loading data from activities.json and sub_activities.json.
        """
        self.activities_percentages = self.load_activity_percentages()
        self.sub_activities = self.load_sub_activities()
        self.validate_percentages()

    def load_activity_percentages(self) -> Dict[str, float]:
        """
        Loads activity percentages from the JSON file.

        :return: Dictionary with activity names as keys and their percentages as values.
        """
        activities_file = os.path.join(Config.DATA_DIR, Config.ACTIVITIES_FILE)
        if not os.path.exists(activities_file):
            raise FileNotFoundError(f"Plik {activities_file} nie został znaleziony.")

        with open(activities_file, 'r', encoding='utf-8') as file:
            try:
                activities = json.load(file)
            except json.JSONDecodeError as error:
                raise ValueError(f"Błąd w pliku JSON: {error}")

        return activities

    def load_sub_activities(self) -> Dict[str, List[str]]:
        """
        Loads sub-activities from the JSON file.

        :return: Dictionary mapping category names to lists of sub-activities.
        """
        sub_activities_file = os.path.join(Config.DATA_DIR, Config.SUB_ACTIVITIES_FILE)
        if not os.path.exists(sub_activities_file):
            raise FileNotFoundError(f"Plik {sub_activities_file} nie został znaleziony.")

        with open(sub_activities_file, 'r', encoding='utf-8') as file:
            try:
                sub_activities = json.load(file)
            except json.JSONDecodeError as error:
                raise ValueError(f"Błąd w pliku JSON: {error}")

        return sub_activities

    def validate_percentages(self):
        """
        Validates that all activity percentage values are floats and sum to approximately 100%.
        """
        total = sum(self.activities_percentages.values())
        for activity, value in self.activities_percentages.items():
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Wartość aktywności '{activity}' nie jest liczbą. Znalazł się: {value}"
                )
            if activity not in self.sub_activities:
                raise ValueError(
                    f"Kategoria aktywności '{activity}' nie ma przypisanych sub-aktywności."
                )

        if not np.isclose(total, 100.0, atol=0.1):
            print(
                f"Informacja: Suma procentów aktywności wynosi {total}%. Normalizuję do 100%."
            )
            self.activities_percentages = {
                key: (value / total) * 100
                for key, value in self.activities_percentages.items()
            }
            total_normalized = sum(self.activities_percentages.values())
            if not np.isclose(total_normalized, 100.0, atol=0.1):
                raise ValueError(
                    f"Suma procentów aktywności po normalizacji wynosi {total_normalized}, ale powinna wynosić około 100."
                )

    def get_random_activity(self, category_name: str) -> str:
        """
        Selects a random sub-activity from the specified category.

        :param category_name: Name of the activity category.
        :return: Selected sub-activity name.
        """
        import random

        category = self.sub_activities.get(category_name)
        if category:
            return random.choice(category)
        else:
            raise ValueError(
                f"Kategoria '{category_name}' nie została znaleziona lub nie ma sub-aktywności."
            )

    def get_categories(self) -> List[str]:
        """
        Retrieves the list of activity categories.

        :return: List of activity category names.
        """
        categories = list(self.activities_percentages.keys())
        print(f"Pobrane kategorie aktywności: {categories}")
        return categories

    def get_percentage(self, category_name: str) -> float:
        """
        Returns the percentage value for a given category.

        :param category_name: Name of the activity category.
        :return: Percentage value.
        """
        return self.activities_percentages.get(category_name, 0.0)
