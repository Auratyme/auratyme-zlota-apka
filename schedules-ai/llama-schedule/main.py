import os
from dotenv import load_dotenv, find_dotenv
import json
import time

from model_loader import LlamaModel
from data_collector import collect_user_data, collect_tasks, collect_user_history

def main():
    """
    Main function demonstrating the use of LlamaModel to generate a daily schedule.
    """

    dotenv_path = find_dotenv('.env.dev', raise_error_if_not_found=False)
    load_dotenv(dotenv_path)

    model_name = os.getenv('MODEL_NAME')
    hf_access_token = os.getenv('HF_ACCESS_TOKEN')

    if not model_name or not hf_access_token:
        print(f"MODEL_NAME: {model_name}")
        print(f"HF_ACCESS_TOKEN: {'*' * len(hf_access_token) if hf_access_token else 'Not set'}")
        raise ValueError("MODEL_NAME and HF_ACCESS_TOKEN must be set in the environment variables.") 

    llama_model = LlamaModel(model_name=model_name, token=hf_access_token)

    user_data = collect_user_data()
    user_history = collect_user_history()
    tasks = collect_tasks()

    max_retries = 3
    for attempt in range(max_retries):
        schedule = llama_model.generate_schedule(tasks, user_data, user_history)

        if schedule:
            print("Generated Daily Schedule:")
            print(json.dumps(schedule, indent=4))
            with open('schedule-data/generated_schedule.json', 'w') as f:
                json.dump(schedule, f, indent=4)
            print("Schedule saved to 'generated_schedule.json'.")
            break
        else:
            print(f"Attempt {attempt + 1} failed to generate a valid schedule.")
            if attempt < max_retries - 1:
                print("Retrying...\n")
                time.sleep(2)
            else:
                print("All attempts failed. Please review the prompt and model configuration.")

if __name__ == "__main__":
    main()
