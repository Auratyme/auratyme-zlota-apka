# utils.py

import importlib
import sys

def check_dependencies():
    """Checks if the required dependencies are installed."""
    required_packages = ['torch', 'transformers', 'huggingface_hub', 'tiktoken', 'blobfile', 'requests']
    missing_packages = []
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            missing_packages.append(package)
    if missing_packages:
        print(f"Missing libraries: {', '.join(missing_packages)}.")
        print(f"Install them using 'pip install {' '.join(missing_packages)}'.")
        sys.exit(1)
