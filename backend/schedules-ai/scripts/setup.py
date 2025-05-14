# === File: scheduler-core/scripts/setup.py ===

"""
Setup Script for the EffectiveDayAI Scheduler Core.

Handles initial environment setup tasks required for development, such as:
- Installing project dependencies using Poetry.
- Creating an example development environment file (.env.dev).
- Checking for essential configuration files.
- Providing guidance on next steps (database setup, RAG indexing - placeholders).

Requires Poetry to be installed (https://python-poetry.org/docs/#installation).
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Project paths (assuming script is in scheduler-core/scripts/)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
ENV_DEV_EXAMPLE_CONTENT: str = """
# Environment variables for development - PLEASE FILL THESE IN
# ----------------------------------------------------------
# Obtain API keys from the respective services.

# Example: OpenRouter (or other LLM provider) API Key
OPENROUTER_API_KEY="your_openrouter_api_key_here"

# Example: Fitbit API Credentials (if using Fitbit integration)
# FITBIT_CLIENT_ID="your_fitbit_client_id"
# FITBIT_CLIENT_SECRET="your_fitbit_client_secret"

# Example: Database Connection URL (if using a database)
# DATABASE_URL="postgresql+asyncpg://user:password@host:port/dbname"

# Add other necessary development environment variables below
# e.g., API keys for weather services, calendar integrations, etc.

"""


# --- Helper Functions ---

def run_command(
    command: Sequence[str],
    cwd: Path = PROJECT_ROOT,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[bool, str, str]:
    """
    Runs a shell command, logs its execution, and captures output.

    Args:
        command (Sequence[str]): The command and its arguments as a list.
        cwd (Path): The working directory to run the command in. Defaults to PROJECT_ROOT.
        env (Optional[Dict[str, str]]): Optional dictionary of environment variables
                                        to add/override for the subprocess.

    Returns:
        Tuple[bool, str, str]: A tuple containing:
            - bool: True if the command executed successfully (exit code 0), False otherwise.
            - str: Captured standard output.
            - str: Captured standard error.
    """
    command_str = " ".join(command)
    logger.info(f"Running command in '{cwd}': {command_str}")

    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            env=full_env,
        )
        stdout = process.stdout.strip() if process.stdout else ""
        stderr = process.stderr.strip() if process.stderr else ""

        if stdout:
            logger.debug(f"Command stdout:\n{stdout}")
        if stderr:
            logger.warning(f"Command stderr:\n{stderr}")

        logger.info(f"Command '{command[0]}' completed successfully.")
        return True, stdout, stderr

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else ""
        logger.error(f"Command '{command[0]}' failed with exit code {e.returncode}.")
        if stderr:
            logger.error(f"Error output:\n{stderr}")
        return False, "", stderr
    except FileNotFoundError:
        logger.error(f"Command not found: '{command[0]}'. Is it installed and in PATH?")
        return False, "", f"Command not found: {command[0]}"
    except Exception as e:
        logger.exception(f"An unexpected error occurred while running command: {command_str}")
        return False, "", str(e)


# --- Setup Steps ---

def install_dependencies() -> bool:
    """Installs project dependencies using Poetry."""
    logger.info("--- Step 1: Installing dependencies via Poetry ---")
    # Check if poetry is installed first? Could run `poetry --version`.
    success, _, stderr = run_command(["poetry", "install"])
    if not success:
        logger.error("Failed to install dependencies using 'poetry install'.")
        if "command not found" in stderr.lower():
             logger.error("Poetry command not found. Please install Poetry: https://python-poetry.org/docs/#installation")
        else:
             logger.error("Please ensure pyproject.toml is valid and dependencies can be resolved.")
        return False
    logger.info("Dependencies installed successfully.")
    return True


def setup_configuration_files() -> bool:
    """Sets up necessary configuration files (e.g., .env.dev)."""
    logger.info("--- Step 2: Setting up configuration files ---")
    env_dev_path = PROJECT_ROOT / ".env.dev"
    env_prod_path = PROJECT_ROOT / ".env" # Standard .env for production secrets

    # Create .env.dev if it doesn't exist
    if not env_dev_path.exists():
        logger.warning(f"Development environment file '{env_dev_path.name}' not found. Creating example.")
        try:
            with open(env_dev_path, "w", encoding="utf-8") as f:
                f.write(ENV_DEV_EXAMPLE_CONTENT.strip() + "\n")
            logger.info(f"Created example '{env_dev_path.name}'.")
            logger.warning(f"IMPORTANT: Please edit '{env_dev_path.name}' and fill in your actual API keys and configurations.")
        except IOError as e:
            logger.error(f"Failed to create '{env_dev_path.name}': {e}")
            return False
    else:
        logger.info(f"Development environment file '{env_dev_path.name}' already exists.")

    # Check for production .env but don't create it
    if not env_prod_path.exists():
        logger.warning(f"Production environment file '{env_prod_path.name}' not found.")
        logger.warning("For production deployments, you MUST create this file and populate it with production secrets and configurations.")
        logger.warning("DO NOT commit the production '.env' file to version control.")
    else:
         logger.info(f"Production environment file '{env_prod_path.name}' exists.")


    # Check for YAML config files (assuming they should exist in the repo)
    default_config = PROJECT_ROOT / "data" / "config" / "default.yaml"
    prod_config = PROJECT_ROOT / "data" / "config" / "production.yaml"
    config_files_ok = True
    if not default_config.is_file():
        logger.error(f"Core configuration file missing: {default_config}")
        config_files_ok = False
    if not prod_config.is_file():
        # Production might be optional for pure dev setup, make it a warning
        logger.warning(f"Production configuration file missing: {prod_config}. Needed for production deployments.")
        # config_files_ok = False # Decide if this is critical for setup script

    if not config_files_ok:
         logger.error("One or more core YAML configuration files are missing from 'data/config/'. Please restore them.")
         # return False # Decide if this is a fatal error for the setup script

    logger.info("Configuration file check complete.")
    return True # Return True even if prod files are missing, but log warnings/errors


def initialize_database_placeholder() -> bool:
    """Placeholder function for database initialization/migration."""
    logger.info("--- Step 3: Initializing database (Placeholder) ---")
    logger.info("This step would typically run database migrations (e.g., using Alembic).")
    # Example command (uncomment and adapt if using Alembic):
    # logger.info("Running 'alembic upgrade head'...")
    # success, _, _ = run_command(["alembic", "upgrade", "head"])
    # if not success:
    #     logger.error("Database migration failed.")
    #     return False
    # logger.info("Database migrations applied successfully (Placeholder).")
    logger.info("Skipping database initialization (placeholder logic).")
    return True


def populate_rag_placeholder() -> bool:
    """Placeholder function for populating the RAG knowledge base."""
    logger.info("--- Step 4: Populating RAG knowledge base (Placeholder) ---")
    logger.info("This step would typically involve processing source documents and building/updating a vector index.")
    # Example command (uncomment and adapt):
    # rag_script_path = PROJECT_ROOT / "scripts" / "build_rag_index.py"
    # if rag_script_path.is_file():
    #     logger.info(f"Running RAG indexing script: {rag_script_path.name}")
    #     success, _, _ = run_command([sys.executable, str(rag_script_path)]) # Use sys.executable
    #     if not success:
    #         logger.error("RAG knowledge base population failed.")
    #         return False
    #     logger.info("RAG knowledge base populated successfully (Placeholder).")
    # else:
    #      logger.warning(f"RAG indexing script not found at {rag_script_path}. Skipping.")
    logger.info("Skipping RAG knowledge base population (placeholder logic).")
    return True


# --- Main Setup Function ---

def setup_environment() -> bool:
    """
    Runs all the necessary steps to set up the development environment.

    Returns:
        bool: True if all steps completed successfully, False otherwise.
    """
    logger.info("=============================================")
    logger.info("=== Starting Scheduler Core Setup Script ===")
    logger.info("=============================================")

    steps = [
        ("Install Dependencies", install_dependencies),
        ("Setup Configuration Files", setup_configuration_files),
        ("Initialize Database (Placeholder)", initialize_database_placeholder),
        ("Populate RAG KB (Placeholder)", populate_rag_placeholder),
    ]

    all_successful = True
    for name, step_func in steps:
        logger.info(f"\n>>> Running Step: {name} <<<")
        if not step_func():
            logger.error(f"!!! Step '{name}' failed. Aborting setup. !!!")
            all_successful = False
            break
        logger.info(f">>> Step '{name}' completed successfully. <<<")

    logger.info("\n=============================================")
    if all_successful:
        logger.info("=== Scheduler Core Setup Completed Successfully ===")
        logger.info("---------------------------------------------")
        logger.info("Next Steps & Reminders:")
        logger.info(f"  1. IMPORTANT: Edit '.env.dev' and add your API keys/secrets.")
        logger.info(f"  2. For production, create and populate '.env' (DO NOT commit).")
        logger.info(f"  3. Implement actual database migration logic (if needed) in Step 3.")
        logger.info(f"  4. Implement actual RAG indexing logic (if needed) in Step 4.")
        logger.info(f"  5. You can now likely run the application using: uvicorn scheduler-core.api.server:app --reload --env-file .env.dev")
        logger.info("=============================================")
        return True
    else:
        logger.error("=== Scheduler Core Setup Failed ===")
        logger.info("=============================================")
        return False


if __name__ == "__main__":
    if not setup_environment():
        sys.exit(1) # Exit with a non-zero code to indicate failure
    else:
        sys.exit(0) # Exit with zero code for success
