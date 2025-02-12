import os
import requests
from dotenv import load_dotenv, find_dotenv

def load_environment():
    """
    Loads environment variables from the .env.dev file.

    Returns:
        bool: True if the .env.dev file was successfully loaded, False otherwise.
    """
    dotenv_path = find_dotenv('.env.dev', raise_error_if_not_found=False)
    print(f"Path to .env.dev file: {dotenv_path}")
    load_success = load_dotenv(dotenv_path)

    if load_success:
        print(f".env.dev successfully loaded from {dotenv_path}")
    else:
        print(f"Failed to load .env.dev from {dotenv_path}. Ensure the file exists and is correctly formatted.")

    return load_success

def collect_user_data() -> dict:
    """
    Collects user data required for generating the schedule.

    Returns:
        dict: Dictionary containing user data.
    """
    url = os.getenv('USER_DATA_API_URL')
    try:
        response = requests.get(url)
        response.raise_for_status()
        api_data = response.json()

        data = api_data.get("data", {})
        personal_data = data.get("personal_data", {})
        device_data = data.get("device_data", {}).get("smartwatch", {})

        user_data = {
            "Age": personal_data.get("age", 0),
            "Occupation": personal_data.get("occupation", ""),
            "Work_Type": personal_data.get("work_type", "").capitalize(),
            "Has_Children": "Yes" if personal_data.get("has_children", False) else "No",
            "Sleep_Duration": f"{device_data.get('sleep_duration', 0)} hours",
            "Sleep_Quality": device_data.get("sleep_quality", "").capitalize(),
            "Heart_Rate": f"{device_data.get('heart_rate', 0)} bpm",
            "Physical_Activity": device_data.get("physical_activity", "").capitalize(),
            "Stress_Level": str(device_data.get("stress_level", 0))
        }

        return user_data

    except requests.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return {
            "Age": 30,
            "Occupation": "Software Engineer",
            "Work_Type": "Full-time",
            "Has_Children": "Yes",
            "Sleep_Duration": "7 hours",
            "Sleep_Quality": "Good",
            "Heart_Rate": "72 bpm",
            "Physical_Activity": "Moderate exercise",
            "Stress_Level": "Low"
        }

def collect_user_history() -> dict:
    """
    Collects historical data and preferences of the user.

    Returns:
        dict: Dictionary containing user history.
    """
    user_history = {
        "Previous_Overall_Efficiency_Score": 85,
        "Previous_Overall_Satisfaction_Score": 80,
        "Preferred_Time": "Morning for work tasks, Evening for exercise",
        "Task_Duration": {
            "Prepare presentation": "2 hours",
            "Exercise": "30 minutes",
            "Math homework with children": "1 hour"
        },
        "Changes_in_Schedule": "Postponed exercise to evening",
        "Dietary_Habits": "Regular meals, vegetarian diet"
    }

    return user_history

def collect_tasks() -> list:
    """
    Collects the list of tasks the user wants to accomplish.

    Returns:
        list: List of tasks.
    """
    tasks = [
        "Prepare a presentation for a meeting at 10:00 AM",
        "Do 30 minutes of physical exercise",
        "Complete math homework with children",
        "Read a chapter from a literature book",
        "Family dinner in the evening"
    ]

    return tasks
