# === File: scheduler-core/src/services/llm_engine.py ===

"""
LLM integration engine for schedule optimization and refinement.

Handles integration with Large Language Models (LLMs) for various tasks like
schedule generation (from scratch or refining a solver's output), explanation,
and adaptation, using configurable providers and robust error handling.
Incorporates prompt templating and context augmentation.
"""

import json5
import logging
import os
import re
import time as time_module
import asyncio
import aiohttp
import requests
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, date, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union, cast
from uuid import UUID, uuid4
import jinja2
from jinja2 import Environment, BaseLoader, TemplateSyntaxError
from pydantic import Field, validator, HttpUrl, BaseModel, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Application-specific imports for context data classes ---
SleepMetrics = None
ChronotypeProfile = None
Chronotype = None
Task = None
RAGContext = None
RetrievedContext = None
ScheduledTaskInfo = None  # For type hinting the solver schedule input

logger = logging.getLogger(__name__)

try:
    from src.core.sleep import SleepMetrics
except ImportError:
    @dataclass
    class DummySleepMetrics:
        ideal_duration: Optional[timedelta] = None
        ideal_bedtime: Optional[time] = None
        ideal_wake_time: Optional[time] = None
    SleepMetrics = DummySleepMetrics
    logger.warning("Could not import SleepMetrics for LLMEngine context. Using dummy.")

try:
    from src.core.chronotype import ChronotypeProfile, Chronotype
except ImportError:
    @dataclass
    class DummyChronotypeProfile:
        primary_chronotype: str = "Unknown"
        age: Optional[int] = None
        natural_bedtime: Optional[time] = None
        natural_wake_time: Optional[time] = None
    class DummyChronotype(Enum):
        EARLY_BIRD = "early_bird"
        NIGHT_OWL = "night_owl"
        INTERMEDIATE = "intermediate"
        FLEXIBLE = "flexible"
        UNKNOWN = "unknown"
    ChronotypeProfile = DummyChronotypeProfile
    Chronotype = DummyChronotype
    logger.warning("Could not import ChronotypeProfile/Chronotype for LLMEngine context. Using dummies.")

try:
    from src.core.task_prioritizer import Task, TaskPriority, EnergyLevel
except ImportError:
    @dataclass
    class DummyTask:
        id: UUID
        title: str
        duration: timedelta
        priority: Any
        energy_level: Any
        deadline: Optional[datetime] = None
        dependencies: set = field(default_factory=set)
    class DummyTaskPriority(Enum):
        CRITICAL = 5
        HIGH = 4
        MEDIUM = 3
        LOW = 2
        OPTIONAL = 1
    class DummyEnergyLevel(Enum):
        HIGH = 3
        MEDIUM = 2
        LOW = 1
    Task = DummyTask
    TaskPriority = DummyTaskPriority
    EnergyLevel = DummyEnergyLevel
    logger.warning("Could not import Task/Enums for LLMEngine context. Using dummies.")

try:
    from src.adapters.rag_adapter import RAGContext, RetrievedContext
except ImportError:
    @dataclass
    class DummyRetrievedContext:
        content: str
        source: str
    @dataclass
    class DummyRAGContext:
        research_snippets: List[DummyRetrievedContext] = field(default_factory=list)
        best_practices: List[str] = field(default_factory=list)
    RetrievedContext = DummyRetrievedContext
    RAGContext = DummyRAGContext
    logger.warning("Could not import RAGContext/RetrievedContext for LLMEngine context. Using dummies.")

try:
    from src.core.constraint_solver import ScheduledTaskInfo
except ImportError:
    @dataclass
    class DummyScheduledTaskInfo:
        task_id: UUID
        start_time: time
        end_time: time
        task_date: date
    ScheduledTaskInfo = DummyScheduledTaskInfo
    logger.warning("Could not import ScheduledTaskInfo for LLMEngine context. Using dummy.")

# --- LLM Provider Enumeration ---
class ModelProvider(Enum):
    OPENAI = "openai"
    MISTRAL = "mistral"
    HUGGINGFACE = "huggingface"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    OPENROUTER = "openrouter"

# --- Model Configuration ---
class ModelConfig(BaseSettings):
    llm_provider: ModelProvider = Field(default=ModelProvider.OPENROUTER, alias="LLM_PROVIDER")
    llm_model_name: Optional[str] = Field(default=None, alias="LLM_MODEL_NAME")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY", validate_default=False)
    mistral_api_key: Optional[str] = Field(default=None, alias="MISTRAL_API_KEY", validate_default=False)
    huggingface_api_key: Optional[str] = Field(default=None, alias="HUGGINGFACE_API_KEY", validate_default=False)
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY", validate_default=False)
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY", validate_default=False)
    llm_api_base: Optional[Union[HttpUrl, str]] = Field(default=None, alias="LLM_API_BASE")
    llm_temperature: float = Field(default=0.3, ge=0.0, le=2.0, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2048, gt=0, alias="LLM_MAX_TOKENS")
    llm_top_p: float = Field(default=0.9, ge=0.0, le=1.0, alias="LLM_TOP_P")
    llm_max_retries: int = Field(default=3, ge=0, alias="LLM_MAX_RETRIES")
    llm_retry_delay: float = Field(default=1.5, ge=0.0, alias="LLM_RETRY_DELAY")
    llm_site_url: Optional[str] = Field(default=None, alias="LLM_SITE_URL")
    llm_site_name: Optional[str] = Field(default=None, alias="LLM_SITE_NAME")
    llm_request_timeout: float = Field(default=60.0, gt=0, alias="LLM_REQUEST_TIMEOUT")
    api_key: Optional[str] = None
    api_base: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), '..', '..', '.env.dev'),
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    @validator('llm_model_name', pre=True, always=True)
    def set_default_model_name(cls, v, values):
        provider = values.get('llm_provider')
        if v is None:
            defaults = {
                ModelProvider.MISTRAL: "mistralai/Mistral-7B-Instruct-v0.1",
                ModelProvider.OPENAI: "gpt-3.5-turbo",
                ModelProvider.ANTHROPIC: "claude-3-haiku-20240307",
                ModelProvider.HUGGINGFACE: "mistralai/Mistral-7B-Instruct-v0.1",
                ModelProvider.OPENROUTER: "mistralai/mixtral-8x7b-instruct",
                ModelProvider.LOCAL: "local-model"
            }
            return defaults.get(provider)
        return v

    def model_post_init(self, __context: Any) -> None:
        provider_key_map = {
            ModelProvider.OPENAI: self.openai_api_key,
            ModelProvider.MISTRAL: self.mistral_api_key,
            ModelProvider.HUGGINGFACE: self.huggingface_api_key,
            ModelProvider.ANTHROPIC: self.anthropic_api_key,
            ModelProvider.OPENROUTER: self.openrouter_api_key,
        }
        self.api_key = provider_key_map.get(self.llm_provider)
        if self.llm_provider != ModelProvider.LOCAL and not self.api_key:
            env_var_name = f"{self.llm_provider.value.upper()}_API_KEY"
            logger.warning(f"API key for {self.llm_provider.value} not found via field or env var '{env_var_name}'.")
        if self.llm_api_base:
            self.api_base = str(self.llm_api_base)
        elif self.llm_provider != ModelProvider.LOCAL:
            default_bases = {
                ModelProvider.OPENAI: "https://api.openai.com/v1",
                ModelProvider.MISTRAL: "https://api.mistral.ai/v1",
                ModelProvider.ANTHROPIC: "https://api.anthropic.com/v1",
                ModelProvider.HUGGINGFACE: "https://api-inference.huggingface.co/models",
                ModelProvider.OPENROUTER: "https://openrouter.ai/api/v1"
            }
            self.api_base = default_bases.get(self.llm_provider)
        logger.debug(f"Final ModelConfig - Provider: {self.llm_provider.value}, Model: {self.llm_model_name}, API Key Loaded: {bool(self.api_key)}, API Base: {self.api_base}")

# --- Schedule Generation Context ---
# --- Schedule Generation Context ---
@dataclass
class ScheduleGenerationContext:
    """Comprehensive context for generating or refining a personalized 24h schedule."""
    user_id: UUID
    user_name: str
    target_date: date
    user_profile: Optional[ChronotypeProfile] = None #type: ignore
    preferences: Dict[str, Any] = field(default_factory=dict)  # Expected to contain 'activity_goals' list among others
    tasks: List[Task] = field(default_factory=list) #type: ignore
    fixed_events: List[Dict[str, Any]] = field(default_factory=list)
    sleep_recommendation: Optional[SleepMetrics] = None #type: ignore
    energy_pattern: Optional[Dict[int, float]] = None
    wearable_insights: Dict[str, Any] = field(default_factory=dict) # e.g., {'sleep_quality': 'Good', 'stress_level': 'Low'}
    historical_insights: Dict[str, Any] = field(default_factory=dict) # e.g., {'typical_lunch': '13:15', 'common_activity': 'Evening walk'}
    rag_context: Optional[RAGContext] = None #type: ignore
    previous_feedback: Optional[Dict[str, Any]] = None

# --- Jinja2 Prompt Templates ---
# Template do generowania harmonogramu "od zera" (mniej preferowany)
GENERATE_FROM_SCRATCH_PROMPT_TEMPLATE = """
You are Chronos, an expert AI assistant specializing in creating hyper-personalized, optimal daily schedules based on scientific principles and user data.

**Goal:** Generate a complete, optimized 24-hour schedule (00:00 to 23:59) for {{ target_date.strftime('%Y-%m-%d') }} from scratch.

**User & Date Information:**
- Name: {{ user_name }}
- Chronotype: {{ user_profile.primary_chronotype.value if user_profile else 'Unknown' }}
- Age: {{ getattr(user_profile, 'age', 'Unknown') }}

**Sleep Recommendation:**
{% if sleep_recommendation %}
- Sleep: {{ sleep_recommendation.ideal_bedtime.strftime('%H:%M') if sleep_recommendation.ideal_bedtime else 'N/A' }} to {{ sleep_recommendation.ideal_wake_time.strftime('%H:%M') if sleep_recommendation.ideal_wake_time else 'N/A' }} ({{ (sleep_recommendation.ideal_duration.total_seconds() / 3600) | round(1) if sleep_recommendation.ideal_duration else 'N/A' }} hours)
{% else %}
- Assume default 8-hour sleep ending around 07:00.
{% endif %}

**Tasks:**
{% if tasks %}
{% for task in tasks %}
{{ loop.index }}. {{ task.title }} [Duration: {{ (task.duration.total_seconds() / 60) | int }} min, Priority: {{ task.priority.name }}, Energy: {{ task.energy_level.name }}{% if task.deadline %}, Deadline: {{ task.deadline.strftime('%Y-%m-%d %H:%M') }}{% endif %}]
{% endfor %}
{% else %}
- No tasks.
{% endif %}

**Fixed Events:**
{% if fixed_events %}
{% for event in fixed_events %}
{{ loop.index }}. {{ event.get('name', event.get('id', 'Fixed Event')) }} [{{ event.get('start_time') }} - {{ event.get('end_time') }}]
{% endfor %}
{% else %}
- No fixed events.
{% endif %}

**Standard Activities:**
{% set meal_prefs = preferences.get('meals', {}) %}
{% set routine_prefs = preferences.get('routines', {}) %}
- Breakfast: Around {{ meal_prefs.get('breakfast_time', '08:00') }}, for {{ meal_prefs.get('duration_minutes', 30) }} min
- Lunch: Around {{ meal_prefs.get('lunch_time', '13:00') }}, for {{ meal_prefs.get('duration_minutes', 45) }} min
- Dinner: Around {{ meal_prefs.get('dinner_time', '19:00') }}, for {{ meal_prefs.get('duration_minutes', 45) }} min
- Morning Routine: Duration {{ routine_prefs.get('morning_duration_minutes', 30) }} min
- Evening Routine: Duration {{ routine_prefs.get('evening_duration_minutes', 45) }} min

**Energy Pattern:**
{% if energy_pattern %}
{% set energy_list = [] %}
{% for h, level in energy_pattern|dictsort %}
    {% set _ = energy_list.append(h|string + ":00=" + level|string) %}
{% endfor %}
[{{ ", ".join(energy_list) }}]
{% else %}
- Not available. Assume moderate energy.
{% endif %}

**RAG Context:**
{% if rag_context and rag_context.best_practices %}
- Best Practices: {{ rag_context.best_practices | join(", ") }}
{% else %}
- None.
{% endif %}

**Previous Feedback:**
{% if previous_feedback %}
{{ previous_feedback | tojson(indent=2) }}
{% else %}
- None.
{% endif %}

**INSTRUCTIONS:**
Generate a complete, continuous schedule covering 00:00 to 23:59. Fill any gaps with appropriate blocks (break, free_time, or standard activities). Do not leave any gap unassigned. Use the JSON output structure below.

**Output Format:**
{% if format_type == "json" %}
{
  "schedule": [
    {
      "type": "sleep|meal|routine|task|fixed_event|break|free_time",
      "name": "Activity Name",
      "start_time": "HH:MM",
      "end_time": "HH:MM",
      "task_id": "UUID string (if type is 'task')",
      "description": "Optional description"
    }
  ],
  "metrics": {
    "task_completion_estimate_percent": 0-100,
    "energy_alignment_score": 0-100,
    "procrastination_risk": "Low|Medium|High"
  },
  "explanations": {
    "key_decisions": ["Explanation 1", "Explanation 2"],
    "optimization_focus": "Summary of optimization strategy"
  }
}
{% endif %}
Respond ONLY with the valid {{ format_type | upper }} output.
"""

# Template for refining an existing solver schedule
REFINE_SCHEDULE_PROMPT_TEMPLATE = """
You are Chronos, an expert AI assistant for refining daily schedules. You are provided with a schedule skeleton (generated by a constraint solver) that contains key fixed items (tasks, fixed events, and sleep) that satisfy all hard constraints.

**Goal:** Refine and complete this skeleton schedule for {{ target_date.strftime('%Y-%m-%d') }} so that:
- The final schedule covers the full day from 00:00 to 23:59 with no gaps.
- All items from the skeleton remain unchanged (fixed times).
- Any gaps between items are filled with appropriate standard activities (meal, routine), short breaks after long tasks, or labeled as free_time.
- The schedule is optimized based on the user's preferences, energy pattern, and profile.

**User & Date Information:**
- Name: {{ user_name }}
- Chronotype: {{ user_profile.primary_chronotype.value if user_profile else 'Unknown' }}
- Age: {{ getattr(user_profile, 'age', 'Unknown') }}
- Target Date: {{ target_date.strftime('%Y-%m-%d') }}

**Solver Skeleton Schedule:**
{% if solver_schedule %}
{% for item in solver_schedule %}
- {{ item.start_time.strftime('%H:%M') }} - {{ item.end_time.strftime('%H:%M') }}: {{ item.name }} (Type: {{ item.type }}){% if item.task_id %} [ID: {{ item.task_id }}]{% endif %}
{% endfor %}
{% else %}
- No skeleton provided.
{% endif %}

**Standard Activities (to insert in gaps):**
{% set meal_prefs = preferences.get('meals', {}) %}
{% set routine_prefs = preferences.get('routines', {}) %}
- Breakfast: Around {{ meal_prefs.get('breakfast_time', '08:00') }}, duration {{ meal_prefs.get('duration_minutes', 30) }} min
- Lunch: Around {{ meal_prefs.get('lunch_time', '13:00') }}, duration {{ meal_prefs.get('duration_minutes', 45) }} min
- Dinner: Around {{ meal_prefs.get('dinner_time', '19:00') }}, duration {{ meal_prefs.get('duration_minutes', 45) }} min
- Morning Routine: Duration {{ routine_prefs.get('morning_duration_minutes', 30) }} min (after waking)
- Evening Routine: Duration {{ routine_prefs.get('evening_duration_minutes', 45) }} min (before sleep)

**User Activity Goals (to potentially schedule in free time):**
{% set activity_goals = preferences.get('activity_goals', []) %}
{% if activity_goals %}
{% for goal in activity_goals %}
- {{ goal.get('name', 'Unnamed Activity') }}: Duration {{ goal.get('duration_minutes', 60) }} min, Frequency {{ goal.get('frequency', 'as possible') }}, Preferred Time: {{ goal.get('preferred_time', ['any']) | join('/') }}
{% endfor %}
{% else %}
- No specific activity goals defined.
{% endif %}

**Energy Pattern:**
{% if energy_pattern %}
{% set energy_list = [] %}
{% for h, level in energy_pattern|dictsort %}
    {% set _ = energy_list.append(h|string + ":00=" + level|string) %}
{% endfor %}
[{{ ", ".join(energy_list) }}]
{% else %}
- Not available.
{% endif %}

**Recent Context & Habits (Consider these):**
{% if wearable_insights %}
- Last Night's Sleep Quality: {{ wearable_insights.get('sleep_quality', 'N/A') }}
- Recent Stress Level: {{ wearable_insights.get('stress_level', 'N/A') }}
- Readiness Score: {{ wearable_insights.get('readiness_score', 'N/A') }}
- Steps Yesterday: {{ wearable_insights.get('steps_yesterday', 'N/A') }}
- Avg Heart Rate: {{ wearable_insights.get('avg_heart_rate', 'N/A') }}
- Recovery Needed: {{ wearable_insights.get('recovery_needed', 'N/A') }}
- Activity Recommendation: {{ wearable_insights.get('activity_recommendation', 'N/A') }}
- Optimal Focus Periods: {{ wearable_insights.get('focus_periods', []) | join(', ') }}
{% endif %}

{% if historical_insights %}
**Historical Patterns:**
- Typical Lunch Time: {{ historical_insights.get('typical_lunch', 'N/A') }}
- Common Activity: {{ historical_insights.get('common_activity', 'N/A') }}
- Productive Hours: {{ historical_insights.get('productive_hours', []) | join(', ') }}
- Common Break Times: {{ historical_insights.get('common_breaks', []) | join(', ') }}
- Task Completion Success Rate: {{ historical_insights.get('task_completion_success_rate', 'N/A') }}
- Optimal Task Duration: {{ historical_insights.get('optimal_task_duration', 'N/A') }} minutes
- Typical Sleep Duration: {{ historical_insights.get('typical_sleep_duration', 'N/A') }} hours

{% set day_patterns = historical_insights.get('day_specific_patterns', {}) %}
{% if day_patterns %}
**{{ target_date.strftime('%A') }} Specific Patterns:**
- Typical Productivity: {{ day_patterns.get('productivity', 'N/A') }}
- Common Activities: {{ day_patterns.get('common_activities', []) | join(', ') }}
- Typical End Time: {{ day_patterns.get('typical_end_time', 'N/A') }}
{% endif %}
{% endif %}

{% if additional_context %}
**Additional Instructions/Feedback:**
{{ additional_context }}
{% endif %}

**INSTRUCTIONS:**
Refine the above schedule skeleton to create a realistic, human-friendly schedule that covers the full day (00:00-23:59) without gaps.

1. **Respect Core Elements:**
   - DO NOT modify the core fixed events, sleep windows, or scheduled tasks - work around them.
   - Preserve all start and end times from the skeleton schedule.

2. **Add Human Elements:**
   - **Meals:** Add appropriate meal times (breakfast, lunch, dinner) if not already scheduled
   - **Routines:** Include morning routine after waking up and evening routine before sleep
   - **Breaks:** Insert strategic breaks between work/task blocks (5-15 min after 1-2 hours of work)
   - **Physical Activity:** Schedule exercise/movement based on user preferences and wearable data
   - **Personal Time:** Add relaxation, family time, or hobby time in longer gaps

3. **Create Balance:**
   - Ensure no unrealistic work stretches (max 2-3 hours without breaks)
   - Include transition times between activities (5-10 minutes)
   - Balance productive work with personal activities
   - Consider the user's energy pattern throughout the day

4. **Use Context Wisely:**
   - Adapt to the user's chronotype (morning/evening person)
   - Consider wearable data (sleep quality affects morning energy)
   - Use historical patterns (typical meal times, common activities)
   - Respect day-specific patterns (e.g., Mondays vs. Fridays)

5. **Ensure Completeness:**
   - Fill any large gaps with appropriate activities
   - Cover the full 24-hour period (00:00-23:59)
   - Make sure the schedule flows naturally from one activity to the next

**Output Format (JSON):**
{% if format_type == "json" %}
{
  "schedule": [
    {
      "type": "sleep|meal|routine|task|fixed_event|break|free_time",
      "name": "Activity Name",
      "start_time": "HH:MM",
      "end_time": "HH:MM",
      "task_id": "UUID string (only for type 'task')",
      "description": "Optional explanation"
    }
  ],
  "metrics": {
    "task_completion_estimate_percent": 0-100,
    "energy_alignment_score": 0-100,
    "procrastination_risk": "Low|Medium|High"
  },
  "explanations": {
    "key_decisions": ["Explanation 1", "Explanation 2"],
    "optimization_focus": "Summary of optimization strategy"
  }
}
{% endif %}
Respond ONLY with the valid {{ format_type | upper }} output.
"""

# Initialize Jinja2 environment and load templates
try:
    jinja_env = Environment(loader=BaseLoader(), autoescape=False)
    jinja_env.globals['getattr'] = getattr
    jinja_env.globals['timedelta'] = timedelta
    GENERATE_FROM_SCRATCH_TEMPLATE = jinja_env.from_string(GENERATE_FROM_SCRATCH_PROMPT_TEMPLATE)
    REFINE_SCHEDULE_TEMPLATE = jinja_env.from_string(REFINE_SCHEDULE_PROMPT_TEMPLATE)
except TemplateSyntaxError as e:
    logger.error(f"Jinja2 Template Syntax Error: {e}", exc_info=True)
    GENERATE_FROM_SCRATCH_TEMPLATE = None
    REFINE_SCHEDULE_TEMPLATE = None
except Exception as e:
    logger.error(f"Failed to initialize Jinja2 environment: {e}", exc_info=True)
    GENERATE_FROM_SCRATCH_TEMPLATE = None
    REFINE_SCHEDULE_TEMPLATE = None

class LLMEngine:
    """
    Engine for integrating LLMs into schedule optimization and refinement.
    Uses Pydantic for configuration and Jinja2 for prompt templating.
    """
    def __init__(self, config: ModelConfig):
        if not isinstance(config, ModelConfig):
            raise TypeError("config must be an instance of ModelConfig")
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._prompt_template_from_scratch = GENERATE_FROM_SCRATCH_TEMPLATE
        self._prompt_template_refine = REFINE_SCHEDULE_TEMPLATE
        if not self._prompt_template_from_scratch or not self._prompt_template_refine:
            logger.error("One or more Jinja2 prompt templates failed to load.")
        logger.info(f"LLMEngine initialized with {config.llm_provider.value} provider using {config.llm_model_name}")

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def generate_schedule_from_scratch(
        self,
        context: ScheduleGenerationContext,
        format_type: str = "json"
    ) -> Dict[str, Any]:
        logger.warning("generate_schedule_from_scratch is deprecated. Prefer refine_and_complete_schedule.")
        prompt = self._build_prompt(self._prompt_template_from_scratch, context, format_type)
        if not prompt:
            return self._generate_fallback_schedule(context, error_message="Prompt template rendering failed.")
        try:
            response = await self._call_llm_async(prompt)
            schedule = self._process_schedule_response(response, format_type)
            logger.info(f"Successfully generated schedule from scratch for {context.user_name} on {context.target_date}")
            return schedule
        except Exception as e:
            logger.error(f"Error generating schedule from scratch: {e}", exc_info=True)
            return self._generate_fallback_schedule(context, error_message=str(e))

    async def refine_and_complete_schedule(
        self,
        solver_schedule: List[ScheduledTaskInfo], #type: ignore
        context: ScheduleGenerationContext,
        format_type: str = "json"
    ) -> Dict[str, Any]:
        logger.info(f"Refining schedule skeleton for {context.user_name} on {context.target_date}.")
        prompt = self._build_prompt(self._prompt_template_refine, context, format_type, solver_schedule=solver_schedule)
        if not prompt:
            return self._generate_fallback_schedule(context, error_message="Prompt rendering failed in refinement.")
        try:
            response = await self._call_llm_async(prompt)
            schedule = self._process_schedule_response(response, format_type)
            logger.info(f"Successfully refined schedule for {context.user_name} on {context.target_date}")
            return schedule
        except Exception as e:
            logger.error(f"Error refining schedule: {e}", exc_info=True)
            return self._generate_fallback_schedule(context, error_message=str(e))

    def generate_schedule_sync(
        self,
        context: ScheduleGenerationContext,
        format_type: str = "json"
    ) -> Dict[str, Any]:
        logger.warning("generate_schedule_sync is deprecated. Prefer using async refinement.")
        prompt = self._build_prompt(self._prompt_template_from_scratch, context, format_type)
        if not prompt:
            return self._generate_fallback_schedule(context, error_message="Prompt template rendering failed.")
        try:
            response = self._call_llm_sync(prompt)
            schedule = self._process_schedule_response(response, format_type)
            logger.info(f"Successfully generated schedule (sync) for {context.user_name} on {context.target_date}")
            return schedule
        except Exception as e:
            logger.error(f"Error generating schedule (sync): {e}", exc_info=True)
            return self._generate_fallback_schedule(context, error_message=str(e))

    async def explain_schedule_decision(
        self,
        schedule_item: Dict[str, Any],
        context: ScheduleGenerationContext
    ) -> str:
        item_type = schedule_item.get("type", "unknown")
        item_time_str = schedule_item.get("start_time", "")
        item_name = schedule_item.get("name", "")
        user_chronotype_str = context.user_profile.primary_chronotype.value if context.user_profile else "Unknown"
        user_age = getattr(context.user_profile, 'age', None)
        prompt = f"""
        You are an AI assistant explaining schedule decisions.
        Based on the user's data and preferences below, explain concisely why the following item was scheduled at this specific time:

        Item: {item_name}
        Type: {item_type}
        Scheduled Time: {item_time_str}

        User Context:
        - Chronotype: {user_chronotype_str}
        - Age: {user_age or 'Unknown'}
        - Energy Level at Scheduled Time: {self._get_energy_for_time(context.energy_pattern, item_time_str)}

        Provide a brief, user-friendly explanation (under 50 words).
        """
        try:
            response = await self._call_llm_async(prompt, temperature=0.5, max_tokens=100)
            return response.strip()
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return "Could not generate explanation due to an error."

    async def adapt_from_feedback(
        self,
        previous_schedule: Dict[str, Any],
        feedback: Dict[str, Any],
        context: ScheduleGenerationContext
    ) -> Dict[str, Any]:
        context.previous_feedback = feedback
        feedback_rating = feedback.get("rating", "N/A")
        feedback_text = feedback.get("comment", "No specific comments provided.")
        prompt_addition = f"""
        IMPORTANT FEEDBACK (Rating: {feedback_rating}/5): "{feedback_text}"
        Adjust the schedule to better address the user's concerns.
        """
        prompt = self._build_prompt(self._prompt_template_from_scratch, context, "json", additional_context=prompt_addition)
        if not prompt:
            return self._generate_fallback_schedule(context, error_message="Prompt rendering failed during feedback adaptation.")
        try:
            response = await self._call_llm_async(prompt)
            schedule = self._process_schedule_response(response, "json")
            logger.info(f"Adapted schedule generated based on feedback (Rating: {feedback_rating}/5)")
            return schedule
        except Exception as e:
            logger.error(f"Error adapting schedule from feedback: {e}", exc_info=True)
            return self._generate_fallback_schedule(context, error_message=str(e))

    def _build_prompt(
        self,
        template: Optional[jinja2.Template],
        context: ScheduleGenerationContext,
        format_type: str = "json",
        additional_context: str = "",
        solver_schedule: Optional[List[ScheduledTaskInfo]] = None #type: ignore
    ) -> Optional[str]:
        if template is None:
            logger.error("Cannot build prompt: Template is None.")
            return None
        template_context = {
            "user_id": context.user_id,
            "user_name": context.user_name,
            "target_date": context.target_date,
            "user_profile": context.user_profile,
            "sleep_recommendation": context.sleep_recommendation,
            "tasks": context.tasks,
            "fixed_events": context.fixed_events,
            "preferences": context.preferences,
            "energy_pattern": context.energy_pattern,
            "wearable_insights": context.wearable_insights, # Pass new context fields
            "historical_insights": context.historical_insights, # Pass new context fields
            "rag_context": context.rag_context,
            "previous_feedback": context.previous_feedback,
            "additional_context": additional_context,
            "format_type": format_type,
            "solver_schedule": solver_schedule,
            "TaskPriority": TaskPriority,
            "EnergyLevel": EnergyLevel,
            "timedelta": timedelta
        }
        try:
            prompt = template.render(template_context)
            logger.debug(f"Generated LLM Prompt (first 500 chars):\n{prompt[:500]}...")
            return prompt.strip()
        except Exception as e:
            logger.exception("Error rendering prompt template.")
            return None

    def _process_schedule_response(self, response: str, format_type: str) -> Dict[str, Any]:
        if format_type == "json":
            logger.debug(f"Raw LLM response (first 500 chars): {response[:500]}...")
            try:
                json_str = extract_valid_json(response)
                logger.debug(f"Extracted JSON (first 500 chars): {json_str[:500]}...")
                schedule_data = json5.loads(json_str)
                if not isinstance(schedule_data, dict):
                    raise ValueError("Parsed JSON is not a dictionary.")
                if "schedule" not in schedule_data or not isinstance(schedule_data["schedule"], list):
                    raise ValueError("Invalid schedule format: missing or invalid 'schedule' array.")
                return schedule_data
            except (ValueError, json5.JSONDecodeError) as e:
                logger.error(f"Failed to extract/parse JSON response: {e}")
                match = re.search(r"```json\s*([\s\S]*?)\s*```", response, re.IGNORECASE)
                if match:
                    logger.info("Found JSON in markdown block. Attempting to parse.")
                    try:
                        schedule_data = json5.loads(match.group(1))
                        if "schedule" in schedule_data and isinstance(schedule_data["schedule"], list):
                            return schedule_data
                        else:
                            raise ValueError("Markdown JSON missing 'schedule' array.")
                    except (ValueError, json5.JSONDecodeError) as e_md:
                        logger.error(f"Markdown JSON parse failed: {e_md}")
                logger.debug(f"Raw response: {response}")
                raise ValueError(f"Invalid or non-extractable JSON response: {e}")
            except Exception as e_gen:
                logger.error(f"Unexpected error processing JSON: {e_gen}", exc_info=True)
                raise ValueError(f"Unexpected error processing JSON: {e_gen}")
        else:
            return {"schedule_text": response.strip()}

    def _generate_fallback_schedule(
        self,
        context: ScheduleGenerationContext,
        error_message: str = "LLM generation failed."
    ) -> Dict[str, Any]:
        logger.warning(f"Generating fallback schedule due to error: {error_message}")
        schedule_items = []
        for event in context.fixed_events:
            schedule_items.append({
                "type": "fixed_event",
                "name": event.get('name', 'Fixed Event'),
                "start_time": event.get('start_time', 'N/A'),
                "end_time": event.get('end_time', 'N/A'),
            })
        for task in context.tasks:
            schedule_items.append({
                "type": "task",
                "name": task.title,
                "start_time": "N/A",
                "end_time": "N/A",
                "task_id": str(task.id)
            })
        schedule_items.sort(key=lambda x: x.get('start_time', '99:99'))
        return {
            "schedule": schedule_items,
            "metrics": {"status": "fallback"},
            "explanations": {"error": f"Failed to generate optimized schedule: {error_message}. Displaying basic task list."},
            "warnings": [f"LLM generation failed: {error_message}"]
        }

    async def _call_llm_api(self, provider: ModelProvider, method: str, url: str, headers: Dict, payload: Dict) -> Any:
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
        session_method = getattr(self.session, method.lower())
        for attempt in range(self.config.llm_max_retries + 1):
            try:
                logger.debug(f"API Call Attempt {attempt+1}: {method} {url}")
                async with session_method(url, json=payload, headers=headers, timeout=self.config.llm_request_timeout) as response:
                    status = response.status
                    logger.debug(f"API Response Status: {status}")
                    if status == 401:
                        raise ValueError(f"{provider.value} API Authentication Error")
                    if status == 429:
                        logger.warning(f"{provider.value} API rate limit exceeded. Retrying...")
                    elif status == 503 and provider == ModelProvider.HUGGINGFACE:
                        logger.warning("HuggingFace API is loading. Waiting 15s...")
                        await asyncio.sleep(15)
                        continue
                    elif status != 200:
                        error_text = await response.text()
                        logger.error(f"{provider.value} API error (status {status}): {error_text[:500]}...")
                        if attempt == self.config.llm_max_retries:
                            raise ValueError(f"{provider.value} API error after retries: {status}")
                    else:
                        if 'application/json' in response.headers.get('Content-Type', ''):
                            return await response.json()
                        else:
                            return await response.text()
            except (aiohttp.ClientError, ValueError, asyncio.TimeoutError) as e:
                logger.warning(f"Error during {provider.value} API call (attempt {attempt+1}): {e}")
                if attempt == self.config.llm_max_retries:
                    raise
            except Exception as e:
                logger.exception(f"Unexpected error during {provider.value} API call (attempt {attempt+1})")
                if attempt == self.config.llm_max_retries:
                    raise
            if attempt < self.config.llm_max_retries:
                wait_time = self.config.llm_retry_delay * (2 ** attempt)
                logger.info(f"Waiting {wait_time:.1f}s before retry...")
                await asyncio.sleep(wait_time)
        logger.error(f"{provider.value} API call failed after all retries.")
        raise ValueError(f"{provider.value} API call failed after all retries.")

    def _call_api_sync(self, provider: ModelProvider, method: str, url: str, headers: Dict, payload: Dict) -> Any:
        for attempt in range(self.config.llm_max_retries + 1):
            try:
                logger.debug(f"API Call Attempt {attempt+1}: {method} {url}")
                response = requests.request(method, url, json=payload, headers=headers, timeout=self.config.llm_request_timeout)
                status = response.status_code
                logger.debug(f"API Response Status: {status}")
                if status == 401:
                    raise ValueError(f"{provider.value} API Authentication Error")
                if status == 429:
                    logger.warning(f"{provider.value} API rate limit exceeded. Retrying...")
                elif status == 503 and provider == ModelProvider.HUGGINGFACE:
                    logger.warning("HuggingFace API is loading. Waiting 15s...")
                    time_module.sleep(15)
                    continue
                elif status != 200:
                    logger.error(f"{provider.value} API error (status {status}): {response.text[:500]}...")
                    if attempt == self.config.llm_max_retries:
                        raise ValueError(f"{provider.value} API error after retries: {status}")
                else:
                    if 'application/json' in response.headers.get('Content-Type', ''):
                        return response.json()
                    else:
                        return response.text
            except (requests.RequestException, ValueError) as e:
                logger.warning(f"Error during {provider.value} API call (attempt {attempt+1}): {e}")
                if attempt == self.config.llm_max_retries:
                    raise
            except Exception as e:
                logger.exception(f"Unexpected error during {provider.value} API call (attempt {attempt+1})")
                if attempt == self.config.llm_max_retries:
                    raise
            if attempt < self.config.llm_max_retries:
                wait_time = self.config.llm_retry_delay * (2 ** attempt)
                logger.info(f"Waiting {wait_time:.1f}s before retry...")
                time_module.sleep(wait_time)
        logger.error(f"{provider.value} API call failed after all retries.")
        raise ValueError(f"{provider.value} API call failed after all retries.")

    async def _call_openai_async(self, prompt: str, temperature: float, max_tokens: int) -> str:
        if not self.config.api_key:
            raise ValueError("OpenAI API key missing.")
        if not self.config.api_base:
            raise ValueError("OpenAI API base URL missing.")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.config.api_key}"}
        payload = {"model": self.config.llm_model_name, "messages": [{"role": "user", "content": prompt}],
                   "temperature": temperature, "max_tokens": max_tokens, "top_p": self.config.llm_top_p}
        url = f"{self.config.api_base}/chat/completions"
        try:
            result = await self._call_llm_api(ModelProvider.OPENAI, "POST", url, headers, payload)
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Invalid response from OpenAI: {e}")
            raise ValueError("Invalid response structure from OpenAI") from e

    def _call_openai_sync(self, prompt: str, temperature: float, max_tokens: int) -> str:
        if not self.config.api_key:
            raise ValueError("OpenAI API key missing.")
        if not self.config.api_base:
            raise ValueError("OpenAI API base URL missing.")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.config.api_key}"}
        payload = {"model": self.config.llm_model_name, "messages": [{"role": "user", "content": prompt}],
                   "temperature": temperature, "max_tokens": max_tokens, "top_p": self.config.llm_top_p}
        url = f"{self.config.api_base}/chat/completions"
        try:
            result = self._call_api_sync(ModelProvider.OPENAI, "POST", url, headers, payload)
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Invalid response from OpenAI: {e}")
            raise ValueError("Invalid response structure from OpenAI") from e

    async def _call_mistral_async(self, prompt: str, temperature: float, max_tokens: int) -> str:
        return await self._call_openai_async(prompt, temperature, max_tokens)

    def _call_mistral_sync(self, prompt: str, temperature: float, max_tokens: int) -> str:
        return self._call_openai_sync(prompt, temperature, max_tokens)

    async def _call_huggingface_async(self, prompt: str, temperature: float, max_tokens: int) -> str:
        if not self.config.api_key:
            raise ValueError("HuggingFace API key missing.")
        if not self.config.api_base:
            raise ValueError("HuggingFace API base URL missing.")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.config.api_key}"}
        payload = {"inputs": prompt,
                   "parameters": {"max_new_tokens": max_tokens, "temperature": max(temperature, 0.01),
                                  "top_p": self.config.llm_top_p, "do_sample": True if temperature > 0 else False}}
        url = f"{self.config.api_base}/{self.config.llm_model_name}"
        try:
            result = await self._call_llm_api(ModelProvider.HUGGINGFACE, "POST", url, headers, payload)
            if isinstance(result, list) and result:
                return str(result[0].get("generated_text", result[0])).strip()
            if isinstance(result, dict):
                return str(result.get("generated_text", result)).strip()
            return str(result).strip()
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Invalid response from HuggingFace: {e}")
            raise ValueError("Invalid response structure from HuggingFace") from e

    def _call_huggingface_sync(self, prompt: str, temperature: float, max_tokens: int) -> str:
        if not self.config.api_key:
            raise ValueError("HuggingFace API key missing.")
        if not self.config.api_base:
            raise ValueError("HuggingFace API base URL missing.")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.config.api_key}"}
        payload = {"inputs": prompt,
                   "parameters": {"max_new_tokens": max_tokens, "temperature": max(temperature, 0.01),
                                  "top_p": self.config.llm_top_p, "do_sample": True if temperature > 0 else False}}
        url = f"{self.config.api_base}/{self.config.llm_model_name}"
        try:
            result = self._call_api_sync(ModelProvider.HUGGINGFACE, "POST", url, headers, payload)
            if isinstance(result, list) and result:
                return str(result[0].get("generated_text", result[0])).strip()
            if isinstance(result, dict):
                return str(result.get("generated_text", result)).strip()
            return str(result).strip()
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Invalid response from HuggingFace: {e}")
            raise ValueError("Invalid response structure from HuggingFace") from e

    async def _call_anthropic_async(self, prompt: str, temperature: float, max_tokens: int) -> str:
        if not self.config.api_key:
            raise ValueError("Anthropic API key missing.")
        if not self.config.api_base:
            raise ValueError("Anthropic API base URL missing.")
        headers = {"Content-Type": "application/json", "x-api-key": self.config.api_key, "anthropic-version": "2023-06-01"}
        payload = {"model": self.config.llm_model_name, "messages": [{"role": "user", "content": prompt}],
                   "temperature": temperature, "max_tokens": max_tokens, "top_p": self.config.llm_top_p}
        url = f"{self.config.api_base}/messages"
        try:
            result = await self._call_llm_api(ModelProvider.ANTHROPIC, "POST", url, headers, payload)
            return result["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Invalid response from Anthropic: {e}")
            raise ValueError("Invalid response structure from Anthropic") from e

    def _call_anthropic_sync(self, prompt: str, temperature: float, max_tokens: int) -> str:
        if not self.config.api_key:
            raise ValueError("Anthropic API key missing.")
        if not self.config.api_base:
            raise ValueError("Anthropic API base URL missing.")
        headers = {"Content-Type": "application/json", "x-api-key": self.config.api_key, "anthropic-version": "2023-06-01"}
        payload = {"model": self.config.llm_model_name, "messages": [{"role": "user", "content": prompt}],
                   "temperature": temperature, "max_tokens": max_tokens, "top_p": self.config.llm_top_p}
        url = f"{self.config.api_base}/messages"
        try:
            result = self._call_api_sync(ModelProvider.ANTHROPIC, "POST", url, headers, payload)
            return result["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Invalid response from Anthropic: {e}")
            raise ValueError("Invalid response structure from Anthropic") from e

    async def _call_openrouter_async(self, prompt: str, temperature: float, max_tokens: int) -> str:
        if not self.config.api_key:
            raise ValueError("OpenRouter API key missing.")
        if not self.config.api_base:
            raise ValueError("OpenRouter API base URL missing.")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.config.api_key}"}
        if self.config.llm_site_url:
            headers["HTTP-Referer"] = self.config.llm_site_url
        if self.config.llm_site_name:
            headers["X-Title"] = self.config.llm_site_name
        payload = {"model": self.config.llm_model_name, "messages": [{"role": "user", "content": prompt}],
                   "temperature": temperature, "max_tokens": max_tokens, "top_p": self.config.llm_top_p}
        url = f"{self.config.api_base}/chat/completions"
        try:
            result = await self._call_llm_api(ModelProvider.OPENROUTER, "POST", url, headers, payload)
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Invalid response from OpenRouter: {e}")
            raise ValueError("Invalid response structure from OpenRouter") from e

    def _call_openrouter_sync(self, prompt: str, temperature: float, max_tokens: int) -> str:
        if not self.config.api_key:
            raise ValueError("OpenRouter API key missing.")
        if not self.config.api_base:
            raise ValueError("OpenRouter API base URL missing.")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.config.api_key}"}
        if self.config.llm_site_url:
            headers["HTTP-Referer"] = self.config.llm_site_url
        if self.config.llm_site_name:
            headers["X-Title"] = self.config.llm_site_name
        payload = {"model": self.config.llm_model_name, "messages": [{"role": "user", "content": prompt}],
                   "temperature": temperature, "max_tokens": max_tokens, "top_p": self.config.llm_top_p}
        url = f"{self.config.api_base}/chat/completions"
        try:
            result = self._call_api_sync(ModelProvider.OPENROUTER, "POST", url, headers, payload)
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Invalid response from OpenRouter: {e}")
            raise ValueError("Invalid response structure from OpenRouter") from e

    def _call_local_model(self, prompt: str, temperature: float, max_tokens: int) -> str:
        headers = {"Content-Type": "application/json"}
        payload = {"prompt": prompt, "temperature": temperature, "max_tokens": max_tokens, "top_p": self.config.llm_top_p}
        url = self.config.api_base or "http://localhost:8000/v1/completions"
        logger.debug(f"Calling local model at: {url}")
        try:
            result = self._call_api_sync(ModelProvider.LOCAL, "POST", url, headers, payload)
            if isinstance(result, dict):
                return result.get("text", result.get("choices", [{}])[0].get("text", str(result)))
            return str(result)
        except Exception as e:
            logger.error(f"Error calling local model: {e}", exc_info=True)
            raise ValueError(f"Failed to get response from local model: {e}") from e

    def _get_energy_for_time(self, energy_pattern: Optional[Dict[int, float]], time_str: str) -> str:
        if not energy_pattern or not time_str:
            return "Unknown"
        try:
            hour = int(time_str.split(':')[0])
            energy = energy_pattern.get(hour, 0.5)
            if energy >= 0.8:
                return f"High ({energy:.1f})"
            elif energy >= 0.4:
                return f"Medium ({energy:.1f})"
            else:
                return f"Low ({energy:.1f})"
        except (ValueError, IndexError):
            return "Unknown (invalid time)"

def extract_valid_json(text: str) -> str:
    logger.debug(f"Attempting to extract JSON from text (first 100 chars): {text[:100]}...")
    start_brace = text.find('{')
    start_bracket = text.find('[')
    if start_brace == -1 and start_bracket == -1:
        raise ValueError("No JSON object or array found in response")
    if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        start = start_brace
        open_char, close_char = '{', '}'
    else:
        start = start_bracket
        open_char, close_char = '[', ']'
    open_count = 0
    end = -1
    in_string = False
    escape = False
    for i in range(start, len(text)):
        char = text[i]
        if char == '"' and not escape:
            in_string = not in_string
        elif char == '\\' and not escape:
            escape = True
            continue
        if not in_string:
            if char == open_char:
                open_count += 1
            elif char == close_char:
                open_count -= 1
                if open_count == 0:
                    end = i
                    break
        escape = False
    if end == -1:
        raise ValueError("No balanced JSON object or array found in response")
    extracted = text[start:end+1]
    logger.debug(f"Successfully extracted JSON (first 100 chars): {extracted[:100]}...")
    return extracted

if __name__ == "__main__":
    import asyncio
    import uuid

    async def main():
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger.info("--- Running LLMEngine Example ---")
        try:
            model_config = ModelConfig()
            print(f"Loaded config for provider: {model_config.llm_provider.value}")
            print(f"Using model: {model_config.llm_model_name}")
            print(f"API Key loaded: {bool(model_config.api_key)}")
            print(f"API Base: {model_config.api_base}")
            if model_config.llm_provider != ModelProvider.LOCAL and not model_config.api_key:
                print("\nWARNING: API Key not found. LLM calls may fail.")
        except ValidationError as e:
            print(f"Pydantic Validation Error: {e}")
            return
        except Exception as e:
            logger.error(f"Error initializing ModelConfig: {e}", exc_info=True)
            return

        today = datetime.now(timezone.utc)
        user_id = uuid.uuid4()

        TaskType = Task if Task is not None else lambda **kwargs: kwargs
        ProfileType = ChronotypeProfile if ChronotypeProfile is not None else lambda **kwargs: type('DummyProfile', (object,), {'primary_chronotype': Chronotype.INTERMEDIATE})()
        RAGContextType = RAGContext if RAGContext is not None else lambda **kwargs: {}

        example_tasks_obj = [
            TaskType(
                id=uuid4(),
                title="Write Project Proposal",
                priority=TaskPriority.HIGH,
                energy_level=EnergyLevel.HIGH,
                duration=timedelta(hours=2),
                deadline=today + timedelta(days=1, hours=9)
            ),
            TaskType(
                id=uuid4(),
                title="Team meeting prep",
                priority=TaskPriority.MEDIUM,
                energy_level=EnergyLevel.MEDIUM,
                duration=timedelta(minutes=90)
            ),
            TaskType(
                id=uuid4(),
                title="Review documentation",
                priority=TaskPriority.LOW,
                energy_level=EnergyLevel.MEDIUM,
                duration=timedelta(hours=1)
            )
        ]

        fixed_events = [
            {"id": "lunch", "name": "Lunch Break", "start_time": "12:30", "end_time": "13:15"},
            {"id": "meeting", "name": "Project Sync", "start_time": "15:00", "end_time": "15:30"}
        ]

        energy_pattern = {h: 0.5 for h in range(24)}
        energy_pattern.update({9: 0.8, 10: 0.9, 11: 0.8, 14: 0.7, 15: 0.6})

        context = ScheduleGenerationContext(
            user_id=user_id,
            user_name="Test User",
            target_date=today.date() + timedelta(days=1),
            user_profile=ProfileType(user_id=user_id, primary_chronotype=Chronotype.INTERMEDIATE),
            tasks=example_tasks_obj,
            fixed_events=fixed_events,
            energy_pattern=energy_pattern,
            preferences={"meals": {"breakfast_time": "08:30", "lunch_time": "12:30", "dinner_time": "19:00"}}
        )

        rag = RAGContextType()
        if hasattr(rag, 'best_practices'):
            try:
                rag.best_practices = ["Prioritize tasks with deadlines.", "Take short breaks after focused work."]
            except Exception:
                object.__setattr__(rag, 'best_practices', ["Prioritize tasks with deadlines.", "Take short breaks after focused work."])
        context.rag_context = rag

        engine = LLMEngine(model_config)
        async with engine:
            try:
                print("\n--- Generating Schedule (Async - Refinement Flow) ---")
                # Create a dummy solver schedule (skeleton) for example purposes.
                dummy_solver_schedule = [
                    ScheduledTaskInfo(task_id=example_tasks_obj[0].id, start_time=time(9, 0), end_time=time(11, 0), task_date=context.target_date),
                    ScheduledTaskInfo(task_id=example_tasks_obj[2].id, start_time=time(11, 15), end_time=time(12, 15), task_date=context.target_date)
                ]
                # Optionally, add a sleep block if sleep recommendation is provided.
                if context.sleep_recommendation and context.sleep_recommendation.ideal_bedtime and context.sleep_recommendation.ideal_wake_time:
                    dummy_solver_schedule.append(
                        ScheduledTaskInfo(
                            task_id=uuid4(),
                            start_time=context.sleep_recommendation.ideal_bedtime,
                            end_time=context.sleep_recommendation.ideal_wake_time,
                            task_date=context.target_date
                        )
                    )
                    dummy_solver_schedule.sort(key=lambda x: x.start_time)
                refined_schedule = await engine.refine_and_complete_schedule(dummy_solver_schedule, context)
                print("\n--- Refined Schedule ---")
                print(json5.dumps(refined_schedule, indent=2))
                if refined_schedule.get("schedule"):
                    first_item = refined_schedule["schedule"][0]
                    print(f"\n--- Explaining first item: {first_item.get('name')} ---")
                    explanation = await engine.explain_schedule_decision(first_item, context)
                    print(explanation)
            except ValueError as e:
                print(f"\n--- Schedule Generation Failed ---\nError: {e}")
            except Exception as e:
                print(f"\n--- Unexpected Error ---")
                logger.exception("Unexpected error during example run.")
                print(f"Error: {e}")

    asyncio.run(main())
