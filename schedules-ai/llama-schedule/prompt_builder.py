# prompt_builder.py

def prepare_prompt(tasks: list, user_data: dict, user_history: dict = None) -> str:
    """
    Prepares the prompt for the model based on tasks, user data, and history.

    Args:
        tasks (list): List of tasks provided by the user.
        user_data (dict): User's personal data.
        user_history (dict, optional): Historical data and preferences.

    Returns:
        str: Prepared prompt for the model.
    """
    research = (
        "Include best practices for productivity, such as starting the day with the most important tasks, "
        "taking regular breaks, and maintaining consistent sleep and meal times. "
        "Consider the user's sleep quality, stress levels, and preferred times for activities."
    )

    tasks_text = '\n'.join([f"- {task}" for task in tasks])

    user_data_entries = [f"{key}: {value}" for key, value in user_data.items()]
    user_data_text = '\n'.join(user_data_entries)

    user_history_text = ""
    if user_history:
        user_history_entries = [f"{key}: {value}" for key, value in user_history.items()]
        user_history_text = '\n'.join(user_history_entries)

    example_output = '''
Example Output:
[
    {"start_time": "00:00", "end_time": "07:00"", "task": "Sleep"},
    {"start_time": "07:00", "end_time": "07:30", "task": "Wake up and morning routine"},
    {"start_time": "07:30", "end_time": "08:00", "task": "Breakfast"},
    {"start_time": "08:00", "end_time": "09:00", "task": "Commute to work"},
    {"start_time": "09:00", "end_time": "12:00", "task": "Work on key projects"},
    {"start_time": "12:00", "end_time": "13:00", "task": "Lunch break"},
    {"start_time": "13:00", "end_time": "17:00", "task": "Continue work tasks"},
    {"start_time": "17:00", "end_time": "17:30", "task": "Commute home"},
    {"start_time": "17:30", "end_time": "18:00", "task": "Physical exercise (30 minutes)"},
    {"start_time": "18:00", "end_time": "19:00", "task": "Help children with math homework"},
    {"start_time": "19:00", "end_time": "19:30", "task": "Family dinner"},
    {"start_time": "19:30", "end_time": "20:30", "task": "Read a chapter from a literature book"},
    {"start_time": "20:30", "end_time": "21:00", "task": "Relaxation time"},
    {"start_time": "21:00", "end_time": "21:30", "task": "Prepare for bed"},
    {"start_time": "21:30", "end_time": "00:00", "task": "Sleep"}
]
'''

    prompt = (
        "You are a time management assistant. Based on the following tasks, user data, and user history, "
        "generate an optimal daily schedule for the user.\n\n"
        "Provide the schedule strictly in JSON format, including only the start time, end time, and task description, in English.\n\n"
        "Use the following format:\n\n"
        f"{example_output}\n\n"
        "Begin the JSON array with [ and end with ]. Do not include any additional text before or after the JSON array.\n\n"
        "User Data:\n"
        f"{user_data_text}\n\n"
    )

    if user_history_text:
        prompt += f"User History:\n{user_history_text}\n\n"

    prompt += (
        "Tasks to be completed:\n"
        f"{tasks_text}\n\n"
        "Research and assumptions:\n"
        f"{research}\n\n"
        "BEGIN SCHEDULE_JSON\n"
        "END SCHEDULE_JSON\n"
        "Ensure the schedule spans from 00:00 to 23:59, with time slots that can vary in length, "
        "from 10 minutes to several hours. The schedule should be realistic, with no overlapping tasks, "
        "and maximally efficient in utilizing the available time."
    )

    return prompt
