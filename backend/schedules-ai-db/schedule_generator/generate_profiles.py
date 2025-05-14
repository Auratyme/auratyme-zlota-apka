# generate_profiles.py

import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, time
from typing import List, Dict
from config import Config
import logging
import os
import json

def generate_profiles(num_profiles: int) -> List[Dict]:
    """
    Generates a list of profiles with individual preferences based on statistical distributions.

    Args:
        num_profiles (int): Number of profiles to generate.

    Returns:
        List[Dict]: List of profile dictionaries.
    """
    # Load dataset and compute statistics
    dataset = load_dataset()
    stats = compute_statistics(dataset)

    # Get occupations and their proportions
    occupations = get_occupations_with_proportions()

    # Get cluster proportions based on data
    clusters = get_clusters_with_proportions()

    # Generate list of profiles
    profiles = []
    for person_id in range(1, num_profiles + 1):
        # Determine cluster for this person
        time_pref = sample_cluster(clusters)

        # Determine occupation for this person
        occupation_info = sample_occupation(occupations)

        # Create profile
        profile = create_profile(person_id, occupation_info, time_pref, stats)
        profiles.append(profile)
    return profiles

def load_dataset() -> pd.DataFrame:
    """
    Loads the dataset from the CSV file.

    Returns:
        pd.DataFrame: Loaded dataset.
    """
    dataset_path = Config.DATASET_PATH
    try:
        dataset = pd.read_csv(dataset_path)
        logging.info(f"Loaded dataset from '{dataset_path}'.")
        return dataset
    except FileNotFoundError:
        logging.error(f"Dataset file not found at '{dataset_path}'.")
        raise

def compute_statistics(dataset: pd.DataFrame) -> Dict:
    """
    Computes statistics from the dataset for various activities.

    Args:
        dataset (pd.DataFrame): The dataset.

    Returns:
        Dict: Dictionary of computed statistics.
    """
    # Filter out rows that are not time intervals
    dataset = dataset[dataset['ACL00 (Labels)'].str.contains('From')].copy()

    # Extract time intervals
    dataset['Start_Time'] = dataset['ACL00 (Labels)'].apply(lambda x: datetime.strptime(x.split(' to ')[0][5:], '%H:%M').time())
    dataset['End_Time'] = dataset['ACL00 (Labels)'].apply(lambda x: datetime.strptime(x.split(' to ')[1], '%H:%M').time())

    # Convert time to seconds since midnight for easier calculations
    dataset['Time_Seconds'] = dataset['Start_Time'].apply(lambda t: t.hour * 3600 + t.minute * 60 + t.second)

    # Ensure activity columns are numeric
    activity_columns = ['Personal care except eating', 'Eating', 'Work and study',
                        'Household and family care and related travel', 'Leisure. social and associative life except TV and video',
                        'Television and video', 'Travel to/from work/study', 'Unspecified time use and travel']
    for col in activity_columns:
        dataset[col] = pd.to_numeric(dataset[col], errors='coerce')

    # Wake-up time estimation (when sleep drops below 50%)
    wake_up_data = dataset[dataset['Personal care except eating'] < 50]
    if not wake_up_data.empty:
        avg_wake_time_seconds = wake_up_data['Time_Seconds'].min()
    else:
        avg_wake_time_seconds = 7 * 3600  # Default to 7 AM
    avg_wake_time = seconds_to_time(avg_wake_time_seconds)

    # Bedtime estimation (when sleep rises above 50%)
    bed_time_data = dataset[dataset['Personal care except eating'] > 50]
    if not bed_time_data.empty:
        avg_bed_time_seconds = bed_time_data['Time_Seconds'].max()
    else:
        avg_bed_time_seconds = 23 * 3600  # Default to 11 PM
    avg_bed_time = seconds_to_time(avg_bed_time_seconds)

    # Meal times estimation
    avg_breakfast_time = estimate_meal_time(dataset, meal='Breakfast')
    avg_lunch_time = estimate_meal_time(dataset, meal='Lunch')
    avg_dinner_time = estimate_meal_time(dataset, meal='Dinner')

    stats = {
        'avg_wake_time': avg_wake_time,
        'avg_bed_time': avg_bed_time,
        'avg_breakfast_time': avg_breakfast_time,
        'avg_lunch_time': avg_lunch_time,
        'avg_dinner_time': avg_dinner_time
    }
    return stats

def estimate_meal_time(dataset: pd.DataFrame, meal: str) -> datetime.time:
    """
    Estimates the average time for a given meal based on the dataset.

    Args:
        dataset (pd.DataFrame): The dataset.
        meal (str): Meal name ('Breakfast', 'Lunch', 'Dinner').

    Returns:
        datetime.time: Estimated average meal time.
    """
    if meal == 'Breakfast':
        meal_data = dataset[(dataset['Eating'] > 5) & (dataset['Start_Time'] >= time(6, 0)) & (dataset['Start_Time'] <= time(9, 0))]
    elif meal == 'Lunch':
        meal_data = dataset[(dataset['Eating'] > 5) & (dataset['Start_Time'] >= time(11, 0)) & (dataset['Start_Time'] <= time(14, 0))]
    elif meal == 'Dinner':
        meal_data = dataset[(dataset['Eating'] > 5) & (dataset['Start_Time'] >= time(17, 0)) & (dataset['Start_Time'] <= time(20, 0))]
    else:
        return time(12, 0)  # Default to noon

    if not meal_data.empty:
        avg_meal_time_seconds = meal_data['Time_Seconds'].mean()
    else:
        default_times = {'Breakfast': 7.5 * 3600, 'Lunch': 13 * 3600, 'Dinner': 19 * 3600}
        avg_meal_time_seconds = default_times.get(meal, 12 * 3600)

    return seconds_to_time(avg_meal_time_seconds)

def seconds_to_time(seconds: float) -> datetime.time:
    """
    Converts seconds to time object.

    Args:
        seconds (float): Seconds since midnight.

    Returns:
        datetime.time: Time object.
    """
    seconds = int(seconds) % (24 * 3600)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return time(hours, minutes)

def get_occupations_with_proportions() -> List[Dict]:
    """
    Provides a list of possible occupations with their proportions.

    Returns:
        List[Dict]: List of occupations with work types and proportions.
    """
    return [
        {"Occupation": "Student", "Work_Type": "School", "Proportion": 0.2},
        {"Occupation": "Office Worker", "Work_Type": "On-site", "Proportion": 0.4},
        {"Occupation": "Remote Worker", "Work_Type": "Remote", "Proportion": 0.2},
        {"Occupation": "Freelancer", "Work_Type": "Flexible", "Proportion": 0.1},
        {"Occupation": "Unemployed", "Work_Type": "None", "Proportion": 0.05},
        {"Occupation": "Retired", "Work_Type": "None", "Proportion": 0.05}
    ]

def sample_occupation(occupations: List[Dict]) -> Dict:
    """
    Samples an occupation based on proportions.

    Args:
        occupations (List[Dict]): List of occupations with proportions.

    Returns:
        Dict: Sampled occupation.
    """
    occupations_list = [occ for occ in occupations]
    proportions = [occ['Proportion'] for occ in occupations_list]
    occupation = random.choices(occupations_list, weights=proportions, k=1)[0]
    return occupation

def get_clusters_with_proportions() -> Dict:
    """
    Provides clusters with their proportions.

    Returns:
        Dict: Dictionary with clusters and proportions.
    """
    return {
        'Morning': 0.4,
        'Evening': 0.3,
        'Neutral': 0.3
    }

def sample_cluster(clusters: Dict) -> str:
    """
    Samples a cluster based on proportions.

    Args:
        clusters (Dict): Dictionary with clusters and proportions.

    Returns:
        str: Sampled cluster.
    """
    cluster_names = list(clusters.keys())
    proportions = list(clusters.values())
    cluster = random.choices(cluster_names, weights=proportions, k=1)[0]
    return cluster

def create_profile(person_id: int, occupation_info: Dict, time_pref: str, stats: Dict) -> Dict:
    """
    Creates a single profile with individual preferences.

    Args:
        person_id (int): Unique identifier for the person.
        occupation_info (Dict): Occupation information.
        time_pref (str): Time preference ('Morning', 'Evening', 'Neutral').
        stats (Dict): Statistics computed from the dataset.

    Returns:
        Dict: Profile dictionary.
    """
    occupation = occupation_info["Occupation"]
    work_type = occupation_info["Work_Type"]
    age = assign_age(occupation)
    has_children = assign_has_children(age)
    preferences = generate_individual_preferences(occupation, time_pref, stats)
    profile = {
        "Person_ID": person_id,
        "Age": age,
        "Occupation": occupation,
        "Work_Type": work_type,
        "Has_Children": has_children,
        **preferences
    }
    return profile

def assign_age(occupation: str) -> int:
    """
    Assigns age based on occupation.

    Args:
        occupation (str): Occupation of the person.

    Returns:
        int: Assigned age.
    """
    if occupation == "Student":
        return random.randint(16, 25)
    elif occupation == "Retired":
        return random.randint(65, 80)
    elif occupation == "Unemployed":
        return random.randint(22, 60)
    else:
        return random.randint(22, 65)

def assign_has_children(age: int) -> bool:
    """
    Determines if the person has children based on age.

    Args:
        age (int): Age of the person.

    Returns:
        bool: True if the person has children, False otherwise.
    """
    if age < 25:
        return random.choices([True, False], weights=[0.1, 0.9], k=1)[0]
    elif 25 <= age <= 35:
        return random.choices([True, False], weights=[0.5, 0.5], k=1)[0]
    elif 35 < age <= 50:
        return random.choices([True, False], weights=[0.7, 0.3], k=1)[0]
    else:
        return random.choices([True, False], weights=[0.6, 0.4], k=1)[0]

def generate_individual_preferences(occupation: str, time_pref: str, stats: Dict) -> Dict:
    """
    Generates individual preferences for a profile.

    Args:
        occupation (str): Occupation of the person.
        time_pref (str): Time preference ('Morning', 'Evening', 'Neutral').
        stats (Dict): Statistics computed from the dataset.

    Returns:
        Dict: Dictionary with individual preferences.
    """
    # Generate wake-up time based on time preference and stats
    if time_pref == 'Morning':
        wake_up_time = sample_time(stats['avg_wake_time'], std_minutes=30, min_time='05:00', max_time='07:30')
        bed_time = sample_time(stats['avg_bed_time'], std_minutes=30, min_time='21:00', max_time='23:00')
    elif time_pref == 'Evening':
        wake_up_time = sample_time(stats['avg_wake_time'], std_minutes=30, min_time='08:00', max_time='10:00')
        bed_time = sample_time(stats['avg_bed_time'], std_minutes=30, min_time='23:00', max_time='01:00')
    else:
        wake_up_time = sample_time(stats['avg_wake_time'], std_minutes=30)
        bed_time = sample_time(stats['avg_bed_time'], std_minutes=30)

    # Round times to the nearest 15 minutes
    wake_up_time = round_time_to_nearest_minutes(wake_up_time, base=15)
    bed_time = round_time_to_nearest_minutes(bed_time, base=15)

    morning_routine_duration = max(15, int(np.random.normal(45, 15)))
    evening_routine_duration = max(15, int(np.random.normal(45, 15)))

    # Preferred meal times must be after wake-up time and before bed time
    preferred_meal_times = {}
    meal_times = {
        "breakfast": stats['avg_breakfast_time'],
        "lunch": stats['avg_lunch_time'],
        "dinner": stats['avg_dinner_time']
    }
    for meal, avg_time in meal_times.items():
        # Ensure meal time is after wake-up and before bed time
        min_time = max_time = None
        if meal == "breakfast":
            min_time_dt = datetime.combine(datetime.today(), wake_up_time) + timedelta(minutes=30)
            min_time = min_time_dt.time()
            max_time = time(10, 0)
        elif meal == "dinner":
            min_time = time(17, 0)
            max_time_dt = datetime.combine(datetime.today(), bed_time) - timedelta(minutes=60)
            max_time = max_time_dt.time()
        else:
            # For lunch, set typical time range
            min_time = time(11, 30)
            max_time = time(14, 30)

        # Handle cases where min_time or max_time might be invalid due to earlier calculations
        if min_time >= max_time:
            min_time = max_time

        # Convert times to strings if they are not None
        min_time_str = min_time.strftime("%H:%M") if min_time else None
        max_time_str = max_time.strftime("%H:%M") if max_time else None

        preferred_time = sample_time(avg_time, std_minutes=15, min_time=min_time_str, max_time=max_time_str)
        preferred_time = round_time_to_nearest_minutes(preferred_time, base=15)
        preferred_meal_times[meal] = preferred_time

    work_preferences = assign_work_preferences(occupation, wake_up_time, morning_routine_duration, preferred_meal_times)
    preferences = {
        "Typical_Wake_Up_Time": wake_up_time.strftime("%H:%M"),
        "Typical_Bed_Time": bed_time.strftime("%H:%M"),
        "Morning_Routine_Duration": morning_routine_duration,
        "Evening_Routine_Duration": evening_routine_duration,
        "Preferred_Meal_Times": {
            "breakfast": preferred_meal_times["breakfast"].strftime("%H:%M"),
            "lunch": preferred_meal_times["lunch"].strftime("%H:%M"),
            "dinner": preferred_meal_times["dinner"].strftime("%H:%M")
        },
        **work_preferences
    }
    return preferences

def sample_time(avg_time: datetime.time, std_minutes: int = 30, min_time: str = None, max_time: str = None) -> datetime.time:
    """
    Samples a time based on a normal distribution around avg_time.

    Args:
        avg_time (datetime.time): Average time.
        std_minutes (int): Standard deviation in minutes.
        min_time (str): Minimum time in HH:MM format.
        max_time (str): Maximum time in HH:MM format.

    Returns:
        datetime.time: Sampled time.
    """
    avg_seconds = avg_time.hour * 3600 + avg_time.minute * 60 + avg_time.second
    std_seconds = std_minutes * 60
    sampled_seconds = int(np.random.normal(avg_seconds, std_seconds))

    # Apply min and max constraints
    if min_time:
        min_seconds = time_to_seconds(min_time)
        sampled_seconds = max(sampled_seconds, min_seconds)
    if max_time:
        max_seconds = time_to_seconds(max_time)
        sampled_seconds = min(sampled_seconds, max_seconds)

    # Ensure the time wraps around 24 hours
    sampled_seconds = sampled_seconds % (24 * 3600)
    sampled_time = seconds_to_time(sampled_seconds)
    return sampled_time

def time_to_seconds(time_str: str) -> int:
    """
    Converts a time string in HH:MM format to seconds.

    Args:
        time_str (str): Time string.

    Returns:
        int: Total seconds.
    """
    time_obj = datetime.strptime(time_str, "%H:%M").time()
    return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second

def assign_work_preferences(occupation: str, wake_up_time: datetime.time, morning_routine_duration: int, preferred_meal_times: Dict[str, datetime.time]) -> Dict:
    """
    Assigns preferred work start time and duration based on occupation and profile timings.

    Args:
        occupation (str): Occupation of the person.
        wake_up_time (datetime.time): Wake-up time.
        morning_routine_duration (int): Duration of morning routine in minutes.
        preferred_meal_times (Dict[str, datetime.time]): Preferred meal times.

    Returns:
        Dict: Dictionary with work preferences.
    """
    fmt = "%H:%M"
    wake_up_datetime = datetime.combine(datetime.today(), wake_up_time)
    breakfast_time = preferred_meal_times['breakfast']
    breakfast_duration = 30  # Assuming fixed duration
    earliest_work_start_time = wake_up_datetime + timedelta(minutes=morning_routine_duration + breakfast_duration + 15)  # 15 min buffer

    # Ensure earliest work start time is after breakfast
    breakfast_end_time = datetime.combine(datetime.today(), breakfast_time) + timedelta(minutes=breakfast_duration)
    earliest_work_start_time = max(earliest_work_start_time, breakfast_end_time)

    if occupation in ["Office Worker", "Remote Worker", "Freelancer"]:
        # Preferred work start time between earliest_work_start_time and earliest_work_start_time + 2 hours
        latest_work_start_time = earliest_work_start_time + timedelta(hours=2)
        preferred_work_start_time_dt = generate_random_time_within_range(earliest_work_start_time, latest_work_start_time)
        preferred_work_start_time_dt = datetime.combine(datetime.today(), round_time_to_nearest_minutes(preferred_work_start_time_dt.time(), base=15))
        preferred_work_duration = max(240, int(np.random.normal(480, 60)))  # Mean 8 hours, std dev 1 hour
        preferred_work_start_time = preferred_work_start_time_dt.time().strftime(fmt)
    elif occupation == "Student":
        # Preferred work start time between earliest_work_start_time and earliest_work_start_time +1 hour
        latest_work_start_time = earliest_work_start_time + timedelta(hours=1)
        preferred_work_start_time_dt = generate_random_time_within_range(earliest_work_start_time, latest_work_start_time)
        preferred_work_start_time_dt = datetime.combine(datetime.today(), round_time_to_nearest_minutes(preferred_work_start_time_dt.time(), base=15))
        preferred_work_duration = max(180, int(np.random.normal(360, 60)))  # Mean 6 hours, std dev 1 hour
        preferred_work_start_time = preferred_work_start_time_dt.time().strftime(fmt)
    else:
        preferred_work_start_time = None
        preferred_work_duration = 0

    return {
        "Preferred_Work_Start_Time": preferred_work_start_time,
        "Preferred_Work_Duration": preferred_work_duration
    }

def generate_random_time_within_range(start_time: datetime, end_time: datetime) -> datetime:
    """
    Generates a random datetime within a given range.

    Args:
        start_time (datetime): Start time.
        end_time (datetime): End time.

    Returns:
        datetime: Generated datetime.
    """
    delta = end_time - start_time
    int_delta = int(delta.total_seconds())
    if int_delta <= 0:
        return start_time
    random_second = random.randint(0, int_delta)
    return start_time + timedelta(seconds=random_second)

def save_profiles_to_json(profiles: List[Dict], filename: str = Config.PROFILES_PATH):
    """
    Saves generated profiles to a JSON file.

    Args:
        profiles (List[Dict]): List of profile dictionaries.
        filename (str): Path to the output JSON file.
    """
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(profiles, json_file, indent=4, ensure_ascii=False)
    logging.info(f"Profiles saved to '{filename}'.")

def round_time_to_nearest_minutes(time_obj: datetime.time, base: int = 15) -> datetime.time:
    """
    Rounds a time object to the nearest 'base' minutes.

    Args:
        time_obj (datetime.time): Time object to round.
        base (int): Number of minutes to round to (e.g., 5, 15).

    Returns:
        datetime.time: Rounded time object.
    """
    dt = datetime.combine(datetime.today(), time_obj)
    round_to = base * 60
    seconds = dt.hour * 3600 + dt.minute * 60 + dt.second
    rounding = (seconds + round_to / 2) // round_to * round_to
    new_dt = datetime.fromtimestamp(rounding % (24 * 3600))
    return new_dt.time()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    num_profiles_to_generate = Config.NUM_PROFILES
    generated_profiles = generate_profiles(num_profiles_to_generate)
    save_profiles_to_json(generated_profiles)
