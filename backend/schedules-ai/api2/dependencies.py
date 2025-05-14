# === File: schedules-ai/api/dependencies.py ===

"""
Dependency provider functions for the API.

This module contains functions that provide instances of services/components to API endpoints
via FastAPI's dependency injection system (`Depends`).
"""

import logging
from typing import Optional

from src.adapters.device_adapter import DeviceDataAdapter
from src.adapters.rag_adapter import RAGAdapter
from src.core.chronotype import ChronotypeAnalyzer
from src.core.constraint_solver import ConstraintSchedulerSolver
from src.core.scheduler import Scheduler
from src.core.sleep import SleepCalculator
from src.core.task_prioritizer import TaskPrioritizer
from src.services.analytics import AnalyticsService
from src.services.llm_engine import LLMEngine, ModelConfig, ModelProvider
from src.services.rl_engine import AdaptiveEngineService
from src.services.wearables import WearableService

from feedback.collectors.device_data import DeviceDataCollector
from feedback.collectors.user_input import UserInputCollector
from feedback.processors.analyzer import FeedbackAnalyzer

logger = logging.getLogger(__name__)

# --- Application Configuration ---
app_config = {
    "app_name": "EffectiveDayAI Scheduler Core",
    "cors_origins": [
        "http://localhost",
        "http://localhost:8080",
        "http://localhost:3000",
    ],
    "llm": {
        "provider": "openrouter",
        "model_name": "mistralai/mixtral-8x7b-instruct",
        "site_url": "https://effectiveday.ai",
        "site_name": "EffectiveDay AI",
    },
    "solver": {
        "time_limit": 20.0,
    },
    "rag": {},
    "device_adapter": {},
    "sleep": {},
    "chronotype": {},
    "prioritizer_weights": {},
    "wearables": {},
    "analytics": {},
    "adaptive": {},
    "feedback_storage": {},
    "feedback_nlp": {},
    "scheduler": {},
}


# --- Adapter Dependencies ---

def get_rag_adapter() -> RAGAdapter:
    """Provides an instance of the RAGAdapter."""
    logger.debug("Providing RAGAdapter instance.")
    return RAGAdapter(config=app_config.get("rag"))


def get_device_adapter() -> DeviceDataAdapter:
    """Provides an instance of the DeviceDataAdapter."""
    logger.debug("Providing DeviceDataAdapter instance.")
    return DeviceDataAdapter(config=app_config.get("device_adapter"))


# --- Core Component Dependencies ---

def get_sleep_calculator() -> SleepCalculator:
    """Provides an instance of the SleepCalculator."""
    logger.debug("Providing SleepCalculator instance.")
    return SleepCalculator(config=app_config.get("sleep"))


def get_chronotype_analyzer() -> ChronotypeAnalyzer:
    """Provides an instance of the ChronotypeAnalyzer."""
    logger.debug("Providing ChronotypeAnalyzer instance.")
    return ChronotypeAnalyzer(config=app_config.get("chronotype"))


def get_task_prioritizer() -> TaskPrioritizer:
    """Provides an instance of the TaskPrioritizer."""
    logger.debug("Providing TaskPrioritizer instance.")
    return TaskPrioritizer(weights=app_config.get("prioritizer_weights"))


def get_constraint_solver() -> ConstraintSchedulerSolver:
    """Provides an instance of the ConstraintSchedulerSolver."""
    logger.debug("Providing ConstraintSchedulerSolver instance.")
    return ConstraintSchedulerSolver(config=app_config.get("solver"))


def get_llm_engine() -> Optional[LLMEngine]:
    """
    Provides an instance of the LLMEngine, if configured.

    Returns:
        Optional[LLMEngine]: Configured LLM engine or None if configuration is missing
                            or initialization fails.
    """
    llm_conf = app_config.get("llm")
    if not llm_conf or not llm_conf.get("model_name"):
        logger.warning("LLM Engine not configured (missing 'llm' section or 'model_name').")
        return None

    try:
        provider_str = llm_conf.get("provider", "openrouter")
        try:
            provider = ModelProvider(provider_str)
        except ValueError:
            logger.warning(f"Invalid LLM provider '{provider_str}', defaulting to 'openrouter'.")
            provider = ModelProvider.OPENROUTER

        model_config = ModelConfig(
            provider=provider,
            model_name=llm_conf.get("model_name"),
            site_url=llm_conf.get("site_url"),
            site_name=llm_conf.get("site_name"),
        )
        logger.debug(f"Providing LLMEngine instance for provider: {provider.value}")
        return LLMEngine(config=model_config)
    except Exception as e:
        logger.error(f"Failed to initialize LLMEngine: {e}", exc_info=True)
        return None


# --- Service Dependencies ---

def get_wearable_service(
    adapter: DeviceDataAdapter = get_device_adapter(),
    calculator: SleepCalculator = get_sleep_calculator(),
) -> WearableService:
    """Provides an instance of the WearableService."""
    logger.debug("Providing WearableService instance.")
    return WearableService(
        device_adapter=adapter,
        sleep_calculator=calculator,
        config=app_config.get("wearables"),
    )


def get_analytics_service() -> AnalyticsService:
    """Provides an instance of the AnalyticsService."""
    logger.debug("Providing AnalyticsService instance.")
    return AnalyticsService(config=app_config.get("analytics"))


def get_adaptive_engine_service() -> AdaptiveEngineService:
    """Provides an instance of the AdaptiveEngineService (RL)."""
    logger.debug("Providing AdaptiveEngineService instance.")
    return AdaptiveEngineService(config=app_config.get("adaptive"))


# --- Feedback Dependencies ---

def get_user_input_collector() -> UserInputCollector:
    """Provides an instance of the UserInputCollector."""
    logger.debug("Providing UserInputCollector instance.")
    return UserInputCollector(config=app_config.get("feedback_storage"))


def get_device_data_collector(
    service: WearableService = get_wearable_service(),
) -> DeviceDataCollector:
    """Provides an instance of the DeviceDataCollector."""
    logger.debug("Providing DeviceDataCollector instance.")
    return DeviceDataCollector(
        wearable_service=service,
        config=app_config.get("feedback_storage")
    )


def get_feedback_analyzer() -> FeedbackAnalyzer:
    """Provides an instance of the FeedbackAnalyzer."""
    logger.debug("Providing FeedbackAnalyzer instance.")
    return FeedbackAnalyzer(config=app_config.get("feedback_nlp"))


# --- Main Scheduler Dependency ---

def get_scheduler(
    sleep_calc: SleepCalculator = get_sleep_calculator(),
    chrono_analyzer: ChronotypeAnalyzer = get_chronotype_analyzer(),
    prioritizer: TaskPrioritizer = get_task_prioritizer(),
    solver: ConstraintSchedulerSolver = get_constraint_solver(),
    llm: Optional[LLMEngine] = get_llm_engine(),
) -> Scheduler:
    """
    Provides a fully configured instance of the main Scheduler.

    This is the primary dependency used by schedule generation endpoints.
    """
    logger.debug("Providing Scheduler instance.")
    return Scheduler(
        sleep_calculator=sleep_calc,
        chronotype_analyzer=chrono_analyzer,
        task_prioritizer=prioritizer,
        constraint_solver=solver,
        llm_engine=llm,
        config=app_config.get("scheduler"),
    )
