# main.py

"""
Main module to execute the schedule generation and comparison process.
"""

import os
import pandas as pd
from data_loader import DataLoader, ActivityCategories
from schedule_generator import ScheduleGenerator
from aggregator import Aggregator
from config import Config


def save_schedules(schedules_df: pd.DataFrame):
    """
    Saves the generated schedules to a CSV file.

    :param schedules_df: DataFrame containing all generated schedules.
    """
    os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(Config.OUTPUT_DIR, 'generated_schedules.csv')
    schedules_df = schedules_df[['Date', 'Activity', 'Start_Time', 'End_Time', 'Duration']]
    schedules_df.to_csv(output_file, index=False)


def save_comparison(comparison_df: pd.DataFrame, filename: str):
    """
    Saves the comparison DataFrame to a CSV file.

    :param comparison_df: DataFrame containing comparison results.
    :param filename: Name of the output CSV file.
    """
    if not comparison_df.empty:
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        output_file = os.path.join(Config.OUTPUT_DIR, filename)
        comparison_df.to_csv(output_file, index=False)
        print(f"Zapisano porównanie do pliku '{filename}'.")
    else:
        print(
            f"Plik '{filename}' nie został zapisany, ponieważ DataFrame jest pusty."
        )


def main():
    """
    Main function to load data, generate schedules, aggregate and compare them with schedule_dataset_males_2010 data, and save the results.
    """
    try:
        data_loader = DataLoader()
        schedule_data = data_loader.load_schedule_data()
        activity_categories = data_loader.load_activity_categories()

        schedule_generator = ScheduleGenerator(data_loader)
        schedules_df = schedule_generator.generate_schedules(Config.NUM_SCHEDULES)

        aggregator = Aggregator(schedule_data)
        aggregated_comparison = aggregator.aggregate_schedules(schedules_df)
        detailed_comparison = aggregator.compare_schedules_with_dataset(schedules_df)

        print("\nPorównanie wygenerowanych harmonogramów z danymi schedule_dataset_males_2010:")
        print(aggregated_comparison)

        save_schedules(schedules_df)
        save_comparison(aggregated_comparison, 'aggregation_comparison.csv')
        save_comparison(detailed_comparison, 'detailed_time_interval_comparison.csv')

        print(
            "\nGenerowanie harmonogramów zakończone. Pliki zostały zapisane w folderze 'output'."
        )
    except FileNotFoundError as error:
        print(f"Błąd: {error}")
    except Exception as error:
        print(f"Napotkano nieoczekiwany błąd: {error}")


if __name__ == "__main__":
    main()
