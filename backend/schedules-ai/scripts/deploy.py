# === File: scheduler-core/scripts/deploy.py ===

"""
Deployment Script for the EffectiveDayAI Scheduler Core API.

Provides command-line utilities to automate the process of building the
application's Docker image, pushing it to a container registry, and
triggering deployment to various target environments (e.g., Kubernetes, Cloud Run).

Requires Docker and potentially cloud provider CLIs (like gcloud, kubectl)
to be installed and configured in the execution environment.
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout, # Ensure logs go to stdout
)
logger = logging.getLogger(__name__)

# Project paths (assuming script is in scheduler-core/scripts/)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DOCKERFILE_PATH: Path = PROJECT_ROOT / "Dockerfile"
DEFAULT_IMAGE_NAME: str = "effectivedayai/scheduler-core-api" # Example name


# --- Helper Functions ---

def run_command(
    command: Sequence[str],
    cwd: Path = PROJECT_ROOT,
    env: Optional[Dict[str, str]] = None,
    capture: bool = True,
) -> Tuple[bool, str, str]:
    """
    Runs a shell command, logs its execution, and captures output.

    Args:
        command (Sequence[str]): The command and its arguments as a list.
        cwd (Path): The working directory to run the command in. Defaults to PROJECT_ROOT.
        env (Optional[Dict[str, str]]): Optional dictionary of environment variables
                                        to add/override for the subprocess.
        capture (bool): Whether to capture stdout/stderr. If False, output goes directly
                        to the script's stdout/stderr.

    Returns:
        Tuple[bool, str, str]: A tuple containing:
            - bool: True if the command executed successfully (exit code 0), False otherwise.
            - str: Captured standard output (if capture=True, else empty).
            - str: Captured standard error (if capture=True, else empty).
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
            check=True, # Raise CalledProcessError on non-zero exit code
            capture_output=capture,
            text=True,
            env=full_env,
        )
        stdout = process.stdout.strip() if capture and process.stdout else ""
        stderr = process.stderr.strip() if capture and process.stderr else ""

        if capture:
            if stdout:
                logger.debug(f"Command stdout:\n{stdout}")
            if stderr:
                # Log stderr as warning even on success, as some tools use it for info
                logger.warning(f"Command stderr:\n{stderr}")

        logger.info(f"Command '{command[0]}' completed successfully.")
        return True, stdout, stderr

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if capture and e.stderr else ""
        logger.error(f"Command '{command[0]}' failed with exit code {e.returncode}.")
        if capture and stderr:
            logger.error(f"Error output:\n{stderr}")
        return False, "", stderr
    except FileNotFoundError:
        logger.error(f"Command not found: '{command[0]}'. Is it installed and in PATH?")
        return False, "", f"Command not found: {command[0]}"
    except Exception as e:
        logger.exception(f"An unexpected error occurred while running command: {command_str}")
        return False, "", str(e)


# --- Core Functions ---

def build_docker_image(tag: str, dockerfile: Path = DOCKERFILE_PATH) -> bool:
    """
    Builds the Docker image for the application.

    Args:
        tag (str): The full tag for the Docker image (e.g., 'myimage:latest').
        dockerfile (Path): Path to the Dockerfile.

    Returns:
        bool: True if the build was successful, False otherwise.
    """
    logger.info(f"--- Building Docker image: {tag} ---")
    if not dockerfile.is_file():
        logger.error(f"Dockerfile not found at: {dockerfile}")
        return False

    # Use buildx for potential multi-platform builds or advanced features
    command: List[str] = [
        "docker", "buildx", "build",
        "--platform=linux/amd64", # Example: Specify platform for consistency
        "-t", tag,
        "-f", str(dockerfile),
        str(PROJECT_ROOT), # Build context
        "--load", # Load image into local docker daemon after build
    ]

    success, _, _ = run_command(command, cwd=PROJECT_ROOT)

    if not success:
        logger.error("Docker image build failed.")
        return False

    logger.info(f"Successfully built Docker image: {tag}")
    return True


def push_docker_image(local_tag: str, registry: Optional[str] = None) -> bool:
    """
    Tags and pushes a locally built Docker image to a container registry.

    Args:
        local_tag (str): The tag of the locally built image.
        registry (Optional[str]): The container registry URL prefix
                                  (e.g., 'gcr.io/your-project', 'yourdockerhubuser').
                                  If None, push is skipped.

    Returns:
        bool: True if push was successful or skipped, False on failure.
    """
    logger.info(f"--- Pushing Docker image: {local_tag} ---")
    if not registry:
        logger.warning("No container registry specified (--registry). Skipping push.")
        return True # Not considered a failure

    # Construct the fully qualified image name for the registry
    # Ensure the local tag doesn't already include the registry part
    image_name_part = local_tag.split('/')[-1]
    full_image_name = f"{registry.rstrip('/')}/{image_name_part}"

    # 1. Tag the image
    logger.info(f"Tagging image '{local_tag}' as '{full_image_name}'")
    tag_command: List[str] = ["docker", "tag", local_tag, full_image_name]
    success, _, _ = run_command(tag_command)
    if not success:
        logger.error(f"Failed to tag image.")
        return False

    # 2. Push the image
    logger.info(f"Pushing image '{full_image_name}' to registry '{registry}'")
    push_command: List[str] = ["docker", "push", full_image_name]
    success, _, _ = run_command(push_command)
    if not success:
        logger.error(f"Failed to push image.")
        # Consider attempting to remove the failed tag locally?
        return False

    logger.info(f"Successfully pushed Docker image: {full_image_name}")
    return True


def deploy_application(
    image_tag_with_registry: str,
    environment: str,
    config_path: Optional[str] = None
) -> bool:
    """
    Deploys the application using the specified image to the target environment.

    **Placeholder Implementation:** Requires specific logic for each deployment target.

    Args:
        image_tag_with_registry (str): The full image name including the registry
                                       (e.g., 'gcr.io/your-project/myimage:latest').
        environment (str): The target deployment environment (e.g., 'staging', 'production',
                           'kubernetes', 'cloudrun').
        config_path (Optional[str]): Path to environment-specific deployment
                                     configuration files (e.g., Kustomize overlay,
                                     Cloud Run service YAML).

    Returns:
        bool: True if deployment command(s) were initiated successfully, False otherwise.
              Note: This function might only *start* the deployment process.
    """
    logger.info(f"--- Deploying application image {image_tag_with_registry} to environment: {environment} ---")

    # --- Deployment Logic Placeholder ---
    # This section needs to be implemented based on the actual deployment strategy.
    if environment in ["kubernetes", "staging-k8s", "prod-k8s"]:
        logger.info(f"Initiating deployment to Kubernetes environment: {environment}")
        # Example using Kustomize:
        # kustomize_dir = PROJECT_ROOT / "deploy" / "k8s" / environment
        # if not kustomize_dir.is_dir():
        #     logger.error(f"Kustomize directory not found for environment '{environment}' at: {kustomize_dir}")
        #     return False
        # logger.info(f"Applying Kustomize configuration from: {kustomize_dir}")
        # # Potentially update image tag in kustomization.yaml first
        # # update_kustomize_image_tag(kustomize_dir, image_tag_with_registry)
        # deploy_command = ["kubectl", "apply", "-k", str(kustomize_dir)]
        # success, _, _ = run_command(deploy_command)
        # if not success:
        #     logger.error("Kubernetes deployment command failed.")
        #     return False
        logger.warning(f"Kubernetes deployment logic for environment '{environment}' is not implemented.")
        success = False # Mark as failed until implemented

    elif environment in ["cloudrun", "staging-cr", "prod-cr"]:
        logger.info(f"Initiating deployment to Google Cloud Run environment: {environment}")
        # Example using gcloud CLI:
        # project_id = os.environ.get("GCP_PROJECT_ID") # Load from env or config
        # region = os.environ.get("GCP_REGION", "us-central1") # Load from env or config
        # service_name = f"scheduler-core-{environment}" # Construct service name
        # if not project_id:
        #     logger.error("GCP_PROJECT_ID environment variable not set for Cloud Run deployment.")
        #     return False
        # deploy_command = [
        #     "gcloud", "run", "deploy", service_name,
        #     f"--image={image_tag_with_registry}",
        #     f"--project={project_id}",
        #     f"--region={region}",
        #     "--platform=managed",
        #     # Add other flags as needed: --env-vars-file, --service-account, --cpu, --memory, etc.
        #     # "--allow-unauthenticated" # Or configure IAM for authentication
        # ]
        # success, _, _ = run_command(deploy_command)
        # if not success:
        #     logger.error("Cloud Run deployment command failed.")
        #     return False
        logger.warning(f"Google Cloud Run deployment logic for environment '{environment}' is not implemented.")
        success = False # Mark as failed until implemented

    else:
        logger.error(f"Unsupported deployment environment specified: {environment}")
        return False

    if not success:
         logger.error(f"Deployment to environment '{environment}' failed.")
         return False

    logger.info(f"--- Deployment to {environment} initiated successfully (check platform for status) ---")
    return True


# --- Main Execution ---

def main() -> None:
    """Parses arguments and orchestrates the build/push/deploy process."""
    parser = argparse.ArgumentParser(
        description="Builds and deploys the EffectiveDayAI Scheduler Core API.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--tag",
        type=str,
        default="latest",
        help="Version tag for the Docker image (e.g., '1.0.0', 'latest').",
    )
    parser.add_argument(
        "--image-name",
        type=str,
        default=DEFAULT_IMAGE_NAME,
        help="Base name for the Docker image.",
    )
    parser.add_argument(
        "--env",
        type=str,
        required=True,
        help="Target deployment environment (e.g., 'staging-k8s', 'prod-cr', 'kubernetes', 'cloudrun'). "
             "Specific deployment logic must be implemented for the chosen environment.",
    )
    parser.add_argument(
        "--registry",
        type=str,
        default=os.environ.get("CONTAINER_REGISTRY"), # Try getting from env var
        help="Container registry URL prefix (e.g., 'gcr.io/your-project', 'yourdockerhubuser'). "
             "Overrides CONTAINER_REGISTRY env var. Required for push/deploy unless --skip-push is used.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip the 'docker build' step.",
    )
    parser.add_argument(
        "--skip-push",
        action="store_true",
        help="Skip the 'docker push' step.",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to environment-specific deployment configuration file or directory (optional, usage depends on deploy logic).",
    )

    args = parser.parse_args()

    # Construct the local image tag
    local_image_tag = f"{args.image_name}:{args.tag}"

    # --- Step 1: Build Docker Image ---
    if not args.skip_build:
        if not build_docker_image(local_image_tag, DOCKERFILE_PATH):
            logger.critical("Exiting due to Docker build failure.")
            sys.exit(1)
    else:
        logger.info("Skipping Docker build step as requested.")

    # --- Step 2: Push Docker Image ---
    # Push requires a registry
    if not args.skip_push and not args.registry:
         logger.error("Cannot push image: --registry argument or CONTAINER_REGISTRY environment variable is required.")
         sys.exit(1)

    if not args.skip_push:
        if not push_docker_image(local_image_tag, args.registry):
            logger.critical("Exiting due to Docker push failure.")
            sys.exit(1)
    else:
        logger.info("Skipping Docker push step as requested.")

    # --- Step 3: Deploy Application ---
    # Deployment requires the full image name including the registry
    if not args.registry:
         logger.error("Cannot deploy: --registry argument or CONTAINER_REGISTRY environment variable is required to construct full image name.")
         sys.exit(1)

    # Ensure the tag part is correctly appended if registry was provided
    image_name_part = local_image_tag.split('/')[-1]
    full_image_tag_for_deploy = f"{args.registry.rstrip('/')}/{image_name_part}"

    if not deploy_application(full_image_tag_for_deploy, args.env, args.config):
        logger.critical("Exiting due to deployment failure.")
        sys.exit(1)

    logger.info("Deployment script completed successfully.")


if __name__ == "__main__":
    main()
