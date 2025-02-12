import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import login
from utils import check_dependencies
import sys
import re
import time
import json

from prompt_builder import prepare_prompt

class LlamaModel:
    """Class for loading and interacting with the Llama3.2-3B-Instruct model."""

    def __init__(self, model_name: str, token: str):
        """
        Initializes LlamaModel with the specified model name and access token.

        Args:
            model_name (str): Name of the model on Hugging Face Hub.
            token (str): Access token for authentication.
        """
        check_dependencies()
        if not token:
            print("Access token is not set. Please set the HF_ACCESS_TOKEN environment variable.")
            sys.exit(1)
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
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            print("Loading model...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16 if self.device.type == 'cuda' else torch.float32
            )
            self.model.to(self.device)
            self.model.eval()

            try:
                # self.model = torch.compile(self.model)
                print("Model compiled with torch.compile().")
            except Exception as e:
                print(f"Could not compile the model: {e}")

            if self.device.type == 'cuda':
                torch.backends.cudnn.benchmark = True
                print("Enabled torch.backends.cudnn.benchmark for optimized performance.")

            print(f"Model successfully loaded on device: {self.device}.")

            # Dummy inference to force immediate GPU memory allocation
            with torch.no_grad():
                dummy_input = self.tokenizer.encode("Hello", return_tensors="pt").to(self.device)
                _ = self.model(dummy_input)

        except Exception as e:
            print(f"Error loading model: {e}")
            sys.exit(1)

    def generate_schedule(self, tasks: list, user_data: dict, user_history: dict = None) -> dict:
        """
        Generates an optimal daily schedule based on the user's tasks and data.

        Args:
            tasks (list): List of tasks provided by the user.
            user_data (dict): User's personal data.
            user_history (dict, optional): Historical data and preferences.

        Returns:
            dict: Generated daily schedule in JSON format.
        """
        prompt = prepare_prompt(tasks, user_data, user_history)
        print("Prompt prepared for schedule generation.")
        try:
            input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
            attention_mask = torch.ones_like(input_ids)

            print("Generating schedule...")
            start_time = time.time()

            output_ids = self.model.generate(
                input_ids,
                attention_mask=attention_mask,
                max_new_tokens=1024,
                num_beams=1,
                num_return_sequences=1,
                no_repeat_ngram_size=2,
                early_stopping=True,
                pad_token_id=self.tokenizer.pad_token_id,
                do_sample=True,
                top_p=0.9,
                temperature=0.7
            )

            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"Generation completed in {elapsed_time:.2f} seconds.")

            output_text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)

            schedule_json = self._extract_json(output_text)

            if not schedule_json:
                print("Attempting fallback extraction from generated text.")
                schedule_json = self._fallback_extract(text=output_text)

            return schedule_json
        except Exception as e:
            print(f"Error generating schedule: {e}")
            sys.exit(1)

    def _extract_json(self, text: str) -> dict:
        """
        Extracts JSON data from the generated text.

        Args:
            text (str): The generated text.

        Returns:
            dict: Parsed JSON data.
        """
        try:
            start_marker = "BEGIN SCHEDULE_JSON"
            end_marker = "END SCHEDULE_JSON"

            start = text.find(start_marker)
            end = text.find(end_marker)

            if start != -1 and end != -1:
                json_text = text[start + len(start_marker):end].strip()
                if not json_text:
                    print("No content found between the JSON markers.")
                    print("Generated text:")
                    print(text)
                    return {}
                try:
                    schedule = json.loads(json_text)
                    print("Successfully extracted schedule from the generated text.")
                    return schedule
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON between markers: {e}")
                    print("Extracted JSON text:")
                    print(json_text)
                    print("Full generated text:")
                    print(text)
                    return {}
            else:
                print("Markers for JSON extraction not found. Attempting regex extraction.")
                json_pattern = re.compile(r'\[\s*\{.*?\}\s*\]', re.DOTALL)
                match = json_pattern.search(text)
                if match:
                    json_text = match.group()
                    try:
                        schedule = json.loads(json_text)
                        print("Successfully extracted schedule using regex.")
                        return schedule
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON with regex: {e}")
                        print("Extracted JSON text:")
                        print(json_text)
                        print("Full generated text:")
                        print(text)
                        return {}
                else:
                    print("No JSON array found in the generated text.")
                    print("Generated text:")
                    print(text)
                    return {}
        except Exception as e:
            print(f"Unexpected error during JSON extraction: {e}")
            return {}

    def _fallback_extract(self, text: str) -> dict:
        """
        Attempts to extract schedule information from the generated text without JSON.

        Args:
            text (str): The generated text.

        Returns:
            dict: Parsed schedule data.
        """
        try:
            pattern = re.compile(
                r'{"start_time":\s*"(?P<start_time>\d{2}:\d{2})",\s*"end_time":\s*"(?P<end_time>\d{2}:\d{2})",\s*"task":\s*"(?P<task>.+?)"}',
                re.DOTALL
            )
            matches = pattern.findall(text)
            if matches:
                schedule = []
                for match in matches:
                    schedule.append({
                        "start_time": match[0],
                        "end_time": match[1],
                        "task": match[2].strip()
                    })
                print("Successfully extracted schedule using fallback extraction.")
                return schedule
            else:
                pattern_alt = re.compile(
                    r'(?P<start_time>\d{2}:\d{2})\s*-\s*(?P<end_time>\d{2}:\d{2})\s*:\s*(?P<task>.+)',
                    re.MULTILINE
                )
                matches_alt = pattern_alt.findall(text)
                if matches_alt:
                    schedule = []
                    for match in matches_alt:
                        schedule.append({
                            "start_time": match[0],
                            "end_time": match[1],
                            "task": match[2].strip()
                        })
                    print("Successfully extracted schedule using alternative fallback extraction.")
                    return schedule
                else:
                    print("No schedule tasks matched the fallback extraction patterns.")
                    print("Generated text:")
                    print(text)
                    return {}
        except Exception as e:
            print(f"Unexpected error during fallback extraction: {e}")
            return {}
