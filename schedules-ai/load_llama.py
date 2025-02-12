"""Module for loading and using the Llama3.2-3B-Instruct model with CUDA acceleration."""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import sys
import importlib
from huggingface_hub import login
import time

def _check_dependencies():
    """Checks if the required dependencies are installed."""
    required_packages = ['tiktoken', 'blobfile', 'huggingface_hub']
    missing_packages = []
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            missing_packages.append(package)
    if missing_packages:
        print(f"Missing libraries: {', '.join(missing_packages)}.")
        print(f"Install them using 'pip install {' '.join(missing_packages)}'.")
        sys.exit(1)

class LlamaModel:
    """Class for loading and interacting with the Llama3.2-3B-Instruct model."""

    def __init__(self, model_name: str, token: str):
        """
        Initializes LlamaModel with the specified model name and access token.

        Args:
            model_name (str): Name of the model on Hugging Face Hub.
            token (str): Access token for authentication.
        """
        _check_dependencies()
        login(token=token)
        self.model_name = model_name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = None
        self.model = None
        self._load_model()

    def _load_model(self):
        """Loads the tokenizer and model, then moves the model to the specified device."""
        try:
            print("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, use_fast=True)
            print(f"Tokenizer eos_token_id: {self.tokenizer.eos_token_id}")
            print(f"Tokenizer pad_token_id: {self.tokenizer.pad_token_id}")

            # Set pad_token_id if not defined
            if self.tokenizer.pad_token is None:
                if self.tokenizer.eos_token is not None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                    self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
                    print(f"Set pad_token_id to eos_token_id: {self.tokenizer.pad_token_id}")
                else:
                    # Add a special pad token if eos_token_id is also None
                    self.tokenizer.add_special_tokens({'pad_token': '<PAD>'})
                    self.tokenizer.pad_token_id = self.tokenizer.convert_tokens_to_ids('<PAD>')
                    print(f"Added pad_token: <PAD> with pad_token_id: {self.tokenizer.pad_token_id}")

            print("Loading model...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16 if self.device.type == 'cuda' else torch.float32
            )
            # Resize token embeddings if new tokens were added
            if self.tokenizer.pad_token_id != self.model.config.pad_token_id:
                self.model.resize_token_embeddings(len(self.tokenizer))
                self.model.config.pad_token_id = self.tokenizer.pad_token_id
                print(f"Set model config pad_token_id to: {self.model.config.pad_token_id}")

            print(f"Model config pad_token_id: {self.model.config.pad_token_id}")
            print(f"Tokenizer pad_token_id: {self.tokenizer.pad_token_id}")

            self.model.to(self.device)
            self.model.eval()  # Set the model to evaluation mode

            # Opcjonalnie: Włączenie torch.compile() dla dodatkowej optymalizacji (PyTorch 2.0+)
            try:
                self.model = torch.compile(self.model)
                print("Model compiled with torch.compile().")
            except Exception as e:
                print(f"Could not compile the model: {e}")

            # Włączenie benchmarkingu cudnn
            if self.device.type == 'cuda':
                torch.backends.cudnn.benchmark = True
                print("Enabled torch.backends.cudnn.benchmark for optimized performance.")

            print(f"Model successfully loaded on device: {self.device}.")
        except ImportError as ie:
            print(f"Missing library: {ie.name}. Install it using 'pip install {ie.name}'.")
            sys.exit(1)
        except FileNotFoundError as fnf:
            print(f"Error loading model: {fnf}")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading model: {e}")
            sys.exit(1)

    def generate_schedule(self, tasks: list) -> str:
        """
        Generates an optimal daily schedule based on the user's tasks.

        Args:
            tasks (list): List of tasks provided by the user.

        Returns:
            str: Generated daily schedule.
        """
        prompt = self._prepare_prompt(tasks)
        print("Prompt prepared for schedule generation.")
        try:
            input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
            print(f"Encoded input_ids shape: {input_ids.shape}")
            # Generate with attention_mask
            attention_mask = torch.ones_like(input_ids)
            print(f"Attention mask shape: {attention_mask.shape}")
            print(f"pad_token_id: {self.tokenizer.pad_token_id}")
            print(f"eos_token_id: {self.tokenizer.eos_token_id}")

            print("Generating schedule...")
            start_time = time.time()  # Start timing

            # Generation with pad_token_id, keeping max_length=1024
            output_ids = self.model.generate(
                input_ids,
                attention_mask=attention_mask,
                max_length=2048,               # Keeping max_length=1024 as required
                num_beams=3,                    # Using 3 beams for better quality
                num_return_sequences=1,
                no_repeat_ngram_size=2,
                early_stopping=True,
                pad_token_id=self.tokenizer.pad_token_id,
                do_sample=True,                 # Enable sampling
                top_p=0.95,                     # Top-p sampling
                temperature=0.7                 # Control creativity
            )

            end_time = time.time()  # End timing
            elapsed_time = end_time - start_time
            print(f"Generation completed in {elapsed_time:.2f} seconds.")

            schedule = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
            print("Decoding of generated text completed.")
            return schedule
        except Exception as e:
            print(f"Error generating schedule: {e}")
            sys.exit(1)

    def _prepare_prompt(self, tasks: list, user_data: dict = None) -> str:
        """
        Prepares the prompt for the model based on tasks and productivity research.

        Args:
            tasks (list): List of tasks provided by the user.
            user_data (dict, optional): Additional user data.

        Returns:
            str: Prepared prompt for the model.
        """
        research = (
            "Include best practices for productivity, such as starting the day with the most important tasks, "
            "taking breaks every 90 minutes, and maintaining regular sleep and meal times. "
            "Assume 8 hours of sleep at night, 3 meals a day, and time for relaxation and physical activity."
        )
        tasks_text = '\n'.join([f"- {task}" for task in tasks])

        # Include user data in the prompt if available
        user_data_text = ""
        if user_data:
            user_data_entries = [f"{key}: {value}" for key, value in user_data.items()]
            user_data_text = "\nUser Data:\n" + '\n'.join(user_data_entries)

        prompt = (
            "You are a time management assistant. Based on the following tasks"
            f"{' and user data' if user_data else ''}, generate an optimal daily schedule for the user.\n\n"
            "Tasks to be completed:\n"
            f"{tasks_text}"
            f"{user_data_text}\n\n"
            "Research and assumptions:\n"
            f"{research}\n\n"
            "Please provide the schedule in a clear, hour-by-hour format, starting from the time the user wakes up. "
            "Include time slots for each activity, and ensure the total schedule spans 24 hours. "
            "Do not include any additional commentary or explanations."
        )
        return prompt

def main():
    """Main function demonstrating the use of LlamaModel."""
    # Replace with your new access token
    token = "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"
    model_name = "meta-llama/Llama-3.2-3B-Instruct"

    llama_model = LlamaModel(model_name=model_name, token=token)

    tasks = [
        "Prepare a presentation for a meeting at 10:00 AM",
        "Do 30 minutes of physical exercise",
        "Complete math homework",
        "Read a chapter from a literature book",
        "Meet with friends in the evening"
    ]

    schedule = llama_model.generate_schedule(tasks)
    print("Generated daily schedule:\n")
    print(schedule)

if __name__ == "__main__":
    main()
