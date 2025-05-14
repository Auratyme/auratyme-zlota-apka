# === Plik: src/core/scheduler.py ===

"""
Main Scheduling Orchestration Module.

Koordynuje generowanie spersonalizowanego harmonogramu dnia, korzystając z:
1. SleepCalculator – oblicza rekomendowane okno snu.
2. ChronotypeAnalyzer – tworzy profil chronotypu użytkownika.
3. TaskPrioritizer – generuje wzorzec energii w ciągu dnia.
4. ConstraintSchedulerSolver – tworzy szkielet harmonogramu (zadania + wydarzenia stałe + sen), bez nakładania się bloków.
5. LLMEngine – dopieszcza szkielet (dodaje posiłki, rutyny, przerwy, wypełnia luki) bez modyfikacji godzin podstawowych zadań/wydarzeń.
"""
import logging
import os
import yaml
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from src.core.chronotype import Chronotype, ChronotypeAnalyzer, ChronotypeProfile
from src.core.constraint_solver import (
    ConstraintSchedulerSolver,
    FixedEventInterval,
    ScheduledTaskInfo,
    SolverInput,
    SolverTask,
)
from src.core.sleep import SleepCalculator, SleepMetrics
from src.core.task_prioritizer import (
    EnergyLevel,
    Task,
    TaskPriority,
    TaskPrioritizer,
)
from src.utils.time_utils import (
    parse_duration_string,
    time_to_total_minutes,
    total_minutes_to_time,
)
from src.services.llm_engine import (
    LLMEngine,
    ScheduleGenerationContext,
    RAGContext,
)

logger = logging.getLogger(__name__)
CORE_IMPORTS_OK: bool = True


@dataclass(frozen=True)
class ScheduleInputData:
    """Dane wejściowe potrzebne do wygenerowania harmonogramu."""

    user_id: UUID
    target_date: date
    tasks: List[Task]
    fixed_events_input: List[Dict[str, Any]] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    user_profile_data: Optional[Dict[str, Any]] = None
    wearable_data_today: Optional[Dict[str, Any]] = None
    historical_data: Optional[Any] = None


@dataclass(frozen=True)
class GeneratedSchedule:
    """Reprezentacja wygenerowanego harmonogramu z metadanymi."""

    user_id: UUID
    target_date: date
    schedule_id: UUID = field(default_factory=uuid4)
    scheduled_items: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    explanations: Dict[str, Any] = field(default_factory=dict)
    generation_timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    warnings: List[str] = field(default_factory=list)


class Scheduler:
    """
    Orkiestruje generowanie spersonalizowanego harmonogramu dnia.
    """

    def __init__(
        self,
        sleep_calculator: SleepCalculator,
        chronotype_analyzer: ChronotypeAnalyzer,
        task_prioritizer: TaskPrioritizer,
        constraint_solver: ConstraintSchedulerSolver,
        llm_engine: Optional[LLMEngine] = None,
        # --- Inject services for fetching context data ---
        wearable_service: Optional[Any] = None, # Placeholder for a Wearable Service/Adapter
        history_service: Optional[Any] = None,  # Placeholder for a History Service/Adapter
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Inicjalizuje Scheduler z niezbędnymi komponentami.

        Args:
            sleep_calculator: Komponent obliczający sen.
            chronotype_analyzer: Komponent analizujący chronotyp.
            task_prioritizer: Komponent priorytetyzujący zadania.
            constraint_solver: Komponent rozwiązujący harmonogram bez nakładania.
            llm_engine: Opcjonalny silnik LLM do dopieszczania harmonogramu.
            config: Opcjonalna konfiguracja.

        Raises:
            ImportError: Jeżeli brakuje komponentów core.
        """
        if not CORE_IMPORTS_OK:
            raise ImportError("Brak wymaganych zależności core do inicjalizacji Scheduler.")
        self.sleep_calculator = sleep_calculator
        self.chronotype_analyzer = chronotype_analyzer
        self.task_prioritizer = task_prioritizer
        self.constraint_solver = constraint_solver
        self.llm_engine = llm_engine
        self.wearable_service = wearable_service # Store injected service
        self.history_service = history_service   # Store injected service
        self.config = config or {}
        self._llm_refinement_enabled = (
            llm_engine is not None and self.config.get("use_llm_refinement", True)
        )
        logger.info(
            f"Scheduler zainicjalizowany (LLM dopieszczanie: {self._llm_refinement_enabled})"
        )

    async def generate_schedule(
        self, input_data: ScheduleInputData
    ) -> GeneratedSchedule:
        """
        Główna metoda generująca harmonogram dnia.

        Args:
            input_data: Dane wejściowe do wygenerowania harmonogramu.

        Returns:
            GeneratedSchedule: Obiekt z harmonogramem, metrykami, ostrzeżeniami.
        """
        warnings: List[str] = []
        try:
            # 1) Profil i metryki snu
            profile = self._prepare_profile(input_data)
            sleep_metrics = self._calculate_sleep(profile, input_data)

            # 2) Przygotowanie danych dla solvera
            solver_input = self._prepare_solver_input(
                input_data, profile, sleep_metrics
            )
            if solver_input is None:
                return self._create_empty(
                    input_data,
                    warnings,
                    "Błąd przygotowania danych dla solvera.",
                )

            # 3) Constraint solver
            logger.debug("Uruchamiam ConstraintSchedulerSolver...")
            core_schedule = self.constraint_solver.solve(solver_input)
            if core_schedule is None:
                logger.warning("Solver nie znalazł żadnego rozwiązania.")
                return self._create_empty(
                    input_data,
                    warnings + ["Brak możliwego harmonogramu core."],
                    "Constraint solver nie powiódł się.",
                )

            # 4) Dopieszczanie LLM
            if self._llm_refinement_enabled and self.llm_engine:
                logger.debug("Dopieszczanie harmonogramu za pomocą LLM...")
                context = self._create_llm_context(
                    input_data, profile, sleep_metrics
                )
                llm_output = await self.llm_engine.refine_and_complete_schedule(
                    core_schedule, context
                )
                final_items = llm_output.get("schedule", [])  # type: ignore
                metrics = llm_output.get("metrics", {})  # type: ignore
                explanations = llm_output.get("explanations", {})  # type: ignore
            else:
                final_items = self._process_core_schedule(
                    core_schedule, input_data, sleep_metrics
                )
                metrics = self._calculate_metrics(final_items, input_data.tasks)
                explanations = {}

            return GeneratedSchedule(
                user_id=input_data.user_id,
                target_date=input_data.target_date,
                scheduled_items=final_items,
                metrics=metrics,
                explanations=explanations,
                warnings=warnings,
            )
        except Exception as e:
            logger.exception("Nieoczekiwany błąd podczas generowania harmonogramu.")
            return self._create_empty(
                input_data,
                warnings,
                f"Błąd wewnętrzny: {e}",
            )

    def _prepare_profile(
        self, input_data: ScheduleInputData
    ) -> ChronotypeProfile:
        """
        Tworzy profil chronotypu użytkownika na podstawie danych MEQ lub domyślnie.

        Args:
            input_data: Dane wejściowe.

        Returns:
            ChronotypeProfile: Profil chronotypu.
        """
        try:
            data = input_data.user_profile_data or {}
            meq = data.get("meq_score")
            if meq is not None:
                chrono = self.chronotype_analyzer.determine_chronotype_from_meq(meq)
                return self.chronotype_analyzer.create_chronotype_profile(
                    user_id=input_data.user_id,
                    chronotype=chrono,
                    source="meq",
                )
        except Exception as err:
            logger.warning(f"Błąd parsowania MEQ: {err}")
        return self.chronotype_analyzer.create_chronotype_profile(
            user_id=input_data.user_id,
            chronotype=Chronotype.UNKNOWN,
            source="default",
            age=(input_data.user_profile_data or {}).get("age"),
        )

    def _calculate_sleep(
        self, profile: ChronotypeProfile, input_data: ScheduleInputData
    ) -> SleepMetrics:
        """
        Oblicza rekomendowane okno snu.

        Args:
            profile: Profil chronotypu.
            input_data: Dane wejściowe.

        Returns:
            SleepMetrics: Rekomendacje snu.
        """
        prefs = input_data.preferences
        wake_str = prefs.get("preferred_wake_time")
        target_wake: Optional[time] = None
        if wake_str:
            try:
                target_wake = time.fromisoformat(wake_str)
            except ValueError:
                logger.warning(f"Niepoprawny format preferred_wake_time: {wake_str}")
        try:
            return self.sleep_calculator.calculate_sleep_window(
                age=(input_data.user_profile_data or {}).get("age"),
                chronotype=profile.primary_chronotype,
                sleep_need_scale=prefs.get("sleep_need_scale"),
                chronotype_scale=prefs.get("chronotype_scale"),
                target_wake_time=target_wake,
            )
        except Exception as err:
            logger.error(f"Błąd kalkulacji snu: {err}", exc_info=True)
            return SleepMetrics(
                ideal_duration=timedelta(hours=8),
                ideal_bedtime=time(23, 0),
                ideal_wake_time=time(7, 0),
            )

    def _prepare_solver_input(
        self,
        input_data: ScheduleInputData,
        profile: ChronotypeProfile,
        sleep_metrics: SleepMetrics,
    ) -> Optional[SolverInput]:
        """
        Konwertuje dane wejściowe na SolverInput, dodając sen jako wydarzenie stałe.

        Args:
            input_data: Dane wejściowe.
            profile: Profil chronotypu.
            sleep_metrics: Rekomendacje snu.

        Returns:
            SolverInput lub None jeśli błąd.
        """
        try:
            solver_tasks: List[SolverTask] = []
            for t in input_data.tasks:
                if t.completed:
                    continue
                dur_min: Optional[int] = None
                if isinstance(t.duration, timedelta):
                    dur_min = int(t.duration.total_seconds() // 60)
                elif isinstance(t.duration, str):
                    pd = parse_duration_string(t.duration)
                    if pd:
                        dur_min = int(pd.total_seconds() // 60)
                elif isinstance(t.duration, (int, float)):
                    dur_min = int(t.duration)
                if not dur_min or dur_min <= 0:
                    logger.warning(f"Niepoprawna długość zadania {t.id}: {t.duration}")
                    continue
                es: Optional[int] = None
                le: Optional[int] = None
                if isinstance(t.earliest_start, time):
                    es = time_to_total_minutes(t.earliest_start)
                if isinstance(t.deadline, datetime):
                    dt = t.deadline.astimezone(timezone.utc)
                    day_start = datetime.combine(input_data.target_date, time(0), tzinfo=timezone.utc)
                    le = int((dt - day_start).total_seconds() // 60)
                deps = [d for d in getattr(t, "dependencies", set()) if isinstance(d, UUID)]
                solver_tasks.append(
                    SolverTask(
                        id=t.id,
                        duration_minutes=dur_min,
                        priority=t.priority.value,
                        energy_level=t.energy_level.value,
                        earliest_start_minutes=es,
                        latest_end_minutes=le,
                        dependencies=deps,
                    )
                )
            solver_events: List[FixedEventInterval] = []
            for e in input_data.fixed_events_input:
                st = time.fromisoformat(e.get("start_time"))
                et = time.fromisoformat(e.get("end_time"))
                sm = time_to_total_minutes(st)
                em = 1440 if et == time(0, 0) else time_to_total_minutes(et)
                if em <= sm:
                    em = sm + 1
                solver_events.append(
                    FixedEventInterval(id=e.get("id"), start_minutes=sm, end_minutes=em)
                )
            # Dodaj sen
            sb = time_to_total_minutes(sleep_metrics.ideal_bedtime)
            sw = time_to_total_minutes(sleep_metrics.ideal_wake_time)
            if sb < sw:
                solver_events.append(
                    FixedEventInterval(id="sleep", start_minutes=sb, end_minutes=sw)
                )
            else:
                solver_events.append(
                    FixedEventInterval(
                        id="sleep_prev", start_minutes=sb, end_minutes=1440
                    )
                )
                solver_events.append(
                    FixedEventInterval(id="sleep_next", start_minutes=0, end_minutes=sw)
                )
            energy_pattern = self.task_prioritizer.get_energy_pattern(profile)
            return SolverInput(
                target_date=input_data.target_date,
                day_start_minutes=0,
                day_end_minutes=1440,
                tasks=solver_tasks,
                fixed_events=solver_events,
                user_energy_pattern=energy_pattern,
            )
        except Exception:
            logger.exception("Błąd przygotowania SolverInput.")
            return None

    def _create_llm_context(
        self,
        input_data: ScheduleInputData,
        profile: ChronotypeProfile,
        sleep_metrics: SleepMetrics,
    ) -> ScheduleGenerationContext:
        """
        Tworzy kontekst dla silnika LLM.

        Args:
            input_data: Dane wejściowe.
            profile: Profil chronotypu.
            sleep_metrics: Rekomendacje snu.

        Returns:
            ScheduleGenerationContext.
        """
        return ScheduleGenerationContext(
            user_id=input_data.user_id,
            user_name=(input_data.user_profile_data or {}).get("name", "User"),
            target_date=input_data.target_date,
            user_profile=profile,
            preferences=input_data.preferences,
            tasks=input_data.tasks,
            fixed_events=input_data.fixed_events_input,
            sleep_recommendation=sleep_metrics,
            energy_pattern=self.task_prioritizer.get_energy_pattern(profile),
            wearable_insights=self._get_wearable_insights(input_data),
            historical_insights=self._get_historical_insights(input_data),
            rag_context=RAGContext(), # Assuming RAGContext is handled elsewhere or initialized empty
            previous_feedback=input_data.historical_data, # Assuming historical_data contains feedback (or fetch via history_service)
        )

    def _get_wearable_insights(self, input_data: ScheduleInputData) -> Dict[str, Any]:
        """Fetches and processes wearable insights for better schedule personalization."""
        if self.wearable_service and hasattr(self.wearable_service, 'get_insights_for_day'):
            try:
                # Example: Call the injected service
                # insights = self.wearable_service.get_insights_for_day(
                #     user_id=input_data.user_id,
                #     target_date=input_data.target_date,
                #     raw_data=input_data.wearable_data_today # Pass raw data if needed
                # )
                # return insights or {}
                # --- Placeholder Implementation ---
                logger.info("SIMULATING wearable insights fetch.")
                # Replace with actual call to self.wearable_service.get_insights_for_day(...)

                # Use wearable_data_today if available, otherwise simulate
                if input_data.wearable_data_today:
                    raw_data = input_data.wearable_data_today
                    sleep_quality = raw_data.get("sleep_quality", "Good")
                    stress_level = raw_data.get("stress_level", "Low")
                    readiness_score = raw_data.get("readiness_score", 0.85)
                    steps_yesterday = raw_data.get("steps_yesterday", 8500)
                    avg_heart_rate = raw_data.get("avg_heart_rate", 68)
                else:
                    # Simulate reasonable values
                    sleep_quality = "Good"
                    stress_level = "Low"
                    readiness_score = 0.85
                    steps_yesterday = 8500
                    avg_heart_rate = 68

                # Create a more comprehensive insights dictionary
                simulated_insights = {
                    "sleep_quality": sleep_quality,
                    "stress_level": stress_level,
                    "readiness_score": readiness_score,
                    "steps_yesterday": steps_yesterday,
                    "avg_heart_rate": avg_heart_rate,
                    "recovery_needed": stress_level == "High" or sleep_quality == "Poor",
                    "activity_recommendation": self._get_activity_recommendation(sleep_quality, stress_level, readiness_score),
                    "focus_periods": self._get_focus_periods(sleep_quality, readiness_score)
                }
                return simulated_insights
                # --- End Placeholder ---
            except Exception as e:
                logger.error(f"Error fetching wearable insights: {e}", exc_info=True) # Keep error logging
                return {}
        else:
            logger.debug("Wearable service not available or lacks 'get_insights_for_day' method.")
            return {} # Return empty if no service injected

    def _get_activity_recommendation(self, sleep_quality: str, stress_level: str, readiness_score: float) -> str:
        """Generate activity recommendation based on wearable data."""
        if sleep_quality == "Poor" or stress_level == "High" or readiness_score < 0.6:
            return "Light activity only (walking, stretching)"
        elif sleep_quality == "Fair" or stress_level == "Medium" or readiness_score < 0.8:
            return "Moderate activity (light cardio, yoga)"
        else:
            return "Full intensity workout ok"

    def _get_focus_periods(self, sleep_quality: str, readiness_score: float) -> List[str]:
        """Generate recommended focus periods based on sleep quality and readiness."""
        if sleep_quality == "Poor" or readiness_score < 0.6:
            return ["10:00-11:30"] # Just one shorter focus period when tired
        elif sleep_quality == "Fair" or readiness_score < 0.8:
            return ["09:30-11:30", "15:00-16:30"] # Standard focus periods
        else:
            return ["09:00-12:00", "14:30-17:00"] # Extended focus periods when well-rested

    def _get_historical_insights(self, input_data: ScheduleInputData) -> Dict[str, Any]:
        """Fetches and processes historical insights for better schedule personalization."""
        if self.history_service and hasattr(self.history_service, 'get_recent_patterns'):
            try:
                # Example: Call the injected service
                # patterns = self.history_service.get_recent_patterns(
                #     user_id=input_data.user_id,
                #     lookback_days=7 # Example parameter
                # )
                # return patterns or {}
                # --- Placeholder Implementation ---
                logger.info("SIMULATING historical insights fetch.")
                # Replace with actual call to self.history_service.get_recent_patterns(...)

                # Use historical_data if available, otherwise simulate
                if input_data.historical_data:
                    historical_data = input_data.historical_data
                    # Extract patterns from historical data if available
                    typical_lunch = historical_data.get("typical_lunch_time", "13:05")
                    common_activity = historical_data.get("common_activity", "Evening walk around 18:00")
                    completion_ratio = historical_data.get("task_completion_ratio", 1.1)
                    productive_hours = historical_data.get("productive_hours", ["09:00-12:00", "15:00-17:00"])
                    common_breaks = historical_data.get("common_breaks", ["10:30", "15:30"])
                else:
                    # Simulate reasonable values
                    typical_lunch = "13:05"
                    common_activity = "Evening walk around 18:00"
                    completion_ratio = 1.1
                    productive_hours = ["09:00-12:00", "15:00-17:00"]
                    common_breaks = ["10:30", "15:30"]

                # Create a more comprehensive insights dictionary
                weekday = input_data.target_date.strftime("%a").lower()
                simulated_patterns = {
                    "typical_lunch": typical_lunch,
                    "common_activity": common_activity,
                    "avg_task_completion_time_vs_estimate_ratio": completion_ratio,
                    "productive_hours": productive_hours,
                    "common_breaks": common_breaks,
                    "day_specific_patterns": self._get_day_specific_patterns(weekday),
                    "task_completion_success_rate": 0.85,  # 85% of tasks typically completed
                    "common_distractions": ["email checking", "social media"],
                    "optimal_task_duration": 45,  # minutes before needing a break
                    "typical_sleep_duration": 7.5  # hours
                }
                return simulated_patterns
                # --- End Placeholder ---
            except Exception as e:
                logger.error(f"Error fetching historical insights: {e}", exc_info=True) # Keep error logging
                return {}
        else:
            logger.debug("History service not available or lacks 'get_recent_patterns' method.")
            return {} # Return empty if no service injected

    def _get_day_specific_patterns(self, weekday: str) -> Dict[str, Any]:
        """Generate day-specific patterns based on the day of the week."""
        patterns = {
            "mon": {
                "productivity": "high",
                "common_activities": ["team meeting", "planning"],
                "typical_end_time": "18:00"
            },
            "tue": {
                "productivity": "high",
                "common_activities": ["focused work"],
                "typical_end_time": "18:30"
            },
            "wed": {
                "productivity": "medium",
                "common_activities": ["mid-week review"],
                "typical_end_time": "17:30"
            },
            "thu": {
                "productivity": "medium",
                "common_activities": ["collaborative work"],
                "typical_end_time": "18:00"
            },
            "fri": {
                "productivity": "variable",
                "common_activities": ["weekly wrap-up", "social event"],
                "typical_end_time": "16:30"
            },
            "sat": {
                "productivity": "low",
                "common_activities": ["personal projects", "family time"],
                "typical_end_time": "flexible"
            },
            "sun": {
                "productivity": "low",
                "common_activities": ["preparation for week", "relaxation"],
                "typical_end_time": "flexible"
            }
        }
        return patterns.get(weekday, {"productivity": "medium", "typical_end_time": "18:00"})

    def _process_core_schedule(
        self,
        core_schedule: List[ScheduledTaskInfo],
        input_data: ScheduleInputData,
        sleep_metrics: SleepMetrics,
    ) -> List[Dict[str, Any]]:
        """
        Formatuje wyniki core solvera i wstawia przerwy, posiłki, rutyny i aktywności.

        Args:
            core_schedule: Lista ScheduledTaskInfo.
            input_data: Dane wejściowe.
            sleep_metrics: Rekomendacje snu.

        Returns:
            Lista elementów harmonogramu gotowa do zwrócenia.
        """
        # Pozyskaj wszystkie bloki (zadania + fixed events)
        blocks: List[Tuple[int, int, Dict[str, Any]]] = []
        # fixed events z solver_input
        solver_in = self._prepare_solver_input(
            input_data, self._prepare_profile(input_data), sleep_metrics
        )
        if solver_in:
            for fe in solver_in.fixed_events:
                blocks.append(
                    (
                        fe.start_minutes,
                        fe.end_minutes,
                        {
                            "type": "fixed_event",
                            "event_id": fe.id,
                            "name": fe.id.replace("_", " ").title(),
                            "start_time": total_minutes_to_time(fe.start_minutes).strftime(
                                "%H:%M"
                            ),
                            "end_time": (
                                "24:00"
                                if fe.end_minutes >= 1440
                                else total_minutes_to_time(fe.end_minutes).strftime(
                                    "%H:%M"
                                )
                            ),
                            "duration_minutes": fe.end_minutes - fe.start_minutes,
                        },
                    )
                )
        # zadania
        for info in core_schedule:
            task_name = "Task"
            # Find the original task to get its title
            for task in input_data.tasks:
                if str(task.id) == str(info.task_id):
                    task_name = task.title
                    break

            blocks.append(
                (
                    time_to_total_minutes(info.start_time),
                    time_to_total_minutes(info.end_time),
                    {
                        "type": "task",
                        "task_id": str(info.task_id),
                        "name": task_name,
                        "start_time": info.start_time.strftime("%H:%M"),
                        "end_time": info.end_time.strftime("%H:%M"),
                        "duration_minutes": time_to_total_minutes(info.end_time) - time_to_total_minutes(info.start_time),
                    },
                )
            )

        # Sortowanie
        blocks.sort(key=lambda x: x[0])

        # Pozyskaj preferencje użytkownika
        prefs = input_data.preferences or {}

        # Domyślne czasy posiłków jeśli nie są zdefiniowane
        meal_prefs = prefs.get("meals", {})
        breakfast_time = meal_prefs.get("breakfast_time", "07:30")
        breakfast_duration = meal_prefs.get("breakfast_duration_minutes", 20)
        lunch_time = meal_prefs.get("lunch_time", "12:30")
        lunch_duration = meal_prefs.get("lunch_duration_minutes", 45)
        dinner_time = meal_prefs.get("dinner_time", "19:00")
        dinner_duration = meal_prefs.get("dinner_duration_minutes", 30)

        # Domyślne czasy rutyn
        routine_prefs = prefs.get("routines", {})
        morning_routine_duration = routine_prefs.get("morning_duration_minutes", 30)
        evening_routine_duration = routine_prefs.get("evening_duration_minutes", 45)

        # Cele aktywności
        activity_goals = prefs.get("activity_goals", [])

        # Konwersja czasów posiłków na minuty
        try:
            breakfast_minutes = time_to_total_minutes(time.fromisoformat(breakfast_time))
        except ValueError:
            breakfast_minutes = 450  # 07:30
            logger.warning(f"Niepoprawny format breakfast_time: {breakfast_time}, używam domyślnego 07:30")

        try:
            lunch_minutes = time_to_total_minutes(time.fromisoformat(lunch_time))
        except ValueError:
            lunch_minutes = 750  # 12:30
            logger.warning(f"Niepoprawny format lunch_time: {lunch_time}, używam domyślnego 12:30")

        try:
            dinner_minutes = time_to_total_minutes(time.fromisoformat(dinner_time))
        except ValueError:
            dinner_minutes = 1140  # 19:00
            logger.warning(f"Niepoprawny format dinner_time: {dinner_time}, używam domyślnego 19:00")

        # Znajdź czas pobudki i czas snu
        wake_time_minutes = time_to_total_minutes(sleep_metrics.ideal_wake_time)
        bedtime_minutes = time_to_total_minutes(sleep_metrics.ideal_bedtime)

        # Dodaj rutyny poranne i wieczorne
        morning_routine_start = wake_time_minutes
        morning_routine_end = morning_routine_start + morning_routine_duration

        evening_routine_start = max(0, bedtime_minutes - evening_routine_duration)
        evening_routine_end = bedtime_minutes

        # Dodaj rutyny do bloków
        blocks.append(
            (
                morning_routine_start,
                morning_routine_end,
                {
                    "type": "routine",
                    "name": "Morning Routine",
                    "start_time": total_minutes_to_time(morning_routine_start).strftime("%H:%M"),
                    "end_time": total_minutes_to_time(morning_routine_end).strftime("%H:%M"),
                    "duration_minutes": morning_routine_duration,
                },
            )
        )

        blocks.append(
            (
                evening_routine_start,
                evening_routine_end,
                {
                    "type": "routine",
                    "name": "Evening Routine",
                    "start_time": total_minutes_to_time(evening_routine_start).strftime("%H:%M"),
                    "end_time": total_minutes_to_time(evening_routine_end).strftime("%H:%M"),
                    "duration_minutes": evening_routine_duration,
                },
            )
        )

        # Dodaj posiłki do bloków
        # Sprawdzamy, czy posiłki nie są już zaplanowane jako fixed_events
        has_breakfast = False
        has_lunch = False
        has_dinner = False

        for _, _, meta in blocks:
            if meta["type"] == "fixed_event":
                event_name = meta["name"].lower()
                if "breakfast" in event_name or "śniadanie" in event_name:
                    has_breakfast = True
                elif "lunch" in event_name or "obiad" in event_name:
                    has_lunch = True
                elif "dinner" in event_name or "kolacja" in event_name:
                    has_dinner = True

        # Dodaj posiłki, które nie są jeszcze zaplanowane
        if not has_breakfast:
            blocks.append(
                (
                    breakfast_minutes,
                    breakfast_minutes + breakfast_duration,
                    {
                        "type": "meal",
                        "name": "Breakfast",
                        "start_time": total_minutes_to_time(breakfast_minutes).strftime("%H:%M"),
                        "end_time": total_minutes_to_time(breakfast_minutes + breakfast_duration).strftime("%H:%M"),
                        "duration_minutes": breakfast_duration,
                    },
                )
            )

        if not has_lunch:
            blocks.append(
                (
                    lunch_minutes,
                    lunch_minutes + lunch_duration,
                    {
                        "type": "meal",
                        "name": "Lunch",
                        "start_time": total_minutes_to_time(lunch_minutes).strftime("%H:%M"),
                        "end_time": total_minutes_to_time(lunch_minutes + lunch_duration).strftime("%H:%M"),
                        "duration_minutes": lunch_duration,
                    },
                )
            )

        if not has_dinner:
            blocks.append(
                (
                    dinner_minutes,
                    dinner_minutes + dinner_duration,
                    {
                        "type": "meal",
                        "name": "Dinner",
                        "start_time": total_minutes_to_time(dinner_minutes).strftime("%H:%M"),
                        "end_time": total_minutes_to_time(dinner_minutes + dinner_duration).strftime("%H:%M"),
                        "duration_minutes": dinner_duration,
                    },
                )
            )

        # Dodaj aktywności z celów użytkownika
        # Sprawdź, czy dzisiejszy dzień jest odpowiedni dla danej aktywności
        weekday = input_data.target_date.strftime("%a").lower()

        for activity in activity_goals:
            activity_name = activity.get("name", "Activity")
            activity_duration = activity.get("duration_minutes", 60)
            activity_frequency = activity.get("frequency", "daily").lower()
            preferred_times = activity.get("preferred_time", ["evening"])

            # Sprawdź, czy aktywność powinna być wykonana dzisiaj
            should_schedule = False
            if activity_frequency == "daily":
                should_schedule = True
            elif weekday in activity_frequency.split(","):
                should_schedule = True
            elif activity_frequency.startswith(weekday[:3]):
                should_schedule = True

            if should_schedule:
                # Znajdź odpowiedni czas dla aktywności
                activity_start = None

                # Preferowane czasy
                if "morning" in preferred_times:
                    activity_start = wake_time_minutes + morning_routine_duration + 30  # Po rutynie porannej
                elif "evening" in preferred_times:
                    activity_start = 1080  # 18:00
                elif "afternoon" in preferred_times:
                    activity_start = 900  # 15:00
                elif "before_sleep" in preferred_times:
                    activity_start = evening_routine_start - activity_duration - 30  # Przed rutyną wieczorną
                else:
                    # Domyślnie wieczorem
                    activity_start = 1080  # 18:00

                if activity_start is not None:
                    blocks.append(
                        (
                            activity_start,
                            activity_start + activity_duration,
                            {
                                "type": "activity",
                                "name": activity_name,
                                "start_time": total_minutes_to_time(activity_start).strftime("%H:%M"),
                                "end_time": total_minutes_to_time(activity_start + activity_duration).strftime("%H:%M"),
                                "duration_minutes": activity_duration,
                            },
                        )
                    )

        # Sortowanie po dodaniu wszystkich elementów
        blocks.sort(key=lambda x: x[0])

        # Rozwiązywanie konfliktów - usuwanie nakładających się bloków
        # Priorytet: fixed_event > task > meal > routine > activity > break
        priority_order = {
            "fixed_event": 5,
            "task": 4,
            "meal": 3,
            "routine": 2,
            "activity": 1,
            "break": 0
        }

        # Usuwanie nakładających się bloków
        non_overlapping_blocks = []
        for i, (start, end, meta) in enumerate(blocks):
            # Sprawdź, czy ten blok nakłada się z jakimkolwiek już dodanym blokiem
            overlaps = False
            for j, (existing_start, existing_end, existing_meta) in enumerate(non_overlapping_blocks):
                if max(start, existing_start) < min(end, existing_end):  # Nakładanie
                    overlaps = True
                    # Jeśli obecny blok ma wyższy priorytet, usuń istniejący
                    current_priority = priority_order.get(meta.get("type", "break"), 0)
                    existing_priority = priority_order.get(existing_meta.get("type", "break"), 0)

                    if current_priority > existing_priority:
                        non_overlapping_blocks[j] = (start, end, meta)
                    break

            if not overlaps:
                non_overlapping_blocks.append((start, end, meta))

        # Sortowanie po rozwiązaniu konfliktów
        non_overlapping_blocks.sort(key=lambda x: x[0])

        # Wstawianie przerw między blokami
        final: List[Dict[str, Any]] = []
        prev_end = 0

        for start, end, meta in non_overlapping_blocks:
            if start > prev_end:
                # Przerwa
                gap_duration = start - prev_end

                # Różne typy przerw w zależności od długości
                break_name = "Break"
                break_type = "break"

                if gap_duration >= 120:  # Dłuższa niż 2 godziny
                    break_name = "Free Time"
                    break_type = "free_time"
                elif gap_duration >= 45:  # Między 45 minut a 2 godziny
                    break_name = "Relaxation"
                    break_type = "relaxation"
                elif gap_duration >= 15:  # Między 15 a 45 minut
                    break_name = "Short Break"
                    break_type = "short_break"
                else:  # Krótsza niż 15 minut
                    break_name = "Quick Break"
                    break_type = "quick_break"

                final.append(
                    {
                        "type": break_type,
                        "name": break_name,
                        "start_time": total_minutes_to_time(prev_end).strftime("%H:%M"),
                        "end_time": total_minutes_to_time(start).strftime("%H:%M"),
                        "duration_minutes": gap_duration,
                    }
                )

            final.append(meta)
            prev_end = max(prev_end, end)

        # Dodaj przerwę na koniec dnia, jeśli potrzebna
        if prev_end < 1440:
            gap_duration = 1440 - prev_end
            break_name = "Free Time"
            break_type = "free_time"

            if gap_duration <= 30:
                break_name = "Quick Break"
                break_type = "quick_break"

            final.append(
                {
                    "type": break_type,
                    "name": break_name,
                    "start_time": total_minutes_to_time(prev_end).strftime("%H:%M"),
                    "end_time": "24:00",
                    "duration_minutes": gap_duration,
                }
            )

        return final

    def _calculate_metrics(
        self, items: List[Dict[str, Any]], tasks: List[Task]
    ) -> Dict[str, Any]:
        """
        Oblicza metryki dla gotowego harmonogramu.

        Args:
            items: Lista pozycji w harmonogramie.
            tasks: Oryginalne zadania.

        Returns:
            Słownik metryk.
        """
        try:
            # Podstawowe metryki
            total_task = sum(
                i.get("duration_minutes", 0) for i in items if i.get("type") == "task"
            )

            # Różne typy przerw
            total_break = sum(
                i.get("duration_minutes", 0)
                for i in items
                if i.get("type") in ["break", "quick_break", "short_break", "relaxation", "free_time"]
            )

            # Stałe wydarzenia
            total_fixed = sum(
                i.get("duration_minutes", 0)
                for i in items
                if i.get("type") == "fixed_event"
            )

            # Sen
            total_sleep = sum(
                i.get("duration_minutes", 0)
                for i in items
                if i.get("type") == "fixed_event" and "sleep" in i.get("event_id", "")
            )

            # Posiłki
            total_meal = sum(
                i.get("duration_minutes", 0)
                for i in items
                if i.get("type") == "meal"
            )

            # Rutyny
            total_routine = sum(
                i.get("duration_minutes", 0)
                for i in items
                if i.get("type") == "routine"
            )

            # Aktywności
            total_activity = sum(
                i.get("duration_minutes", 0)
                for i in items
                if i.get("type") == "activity"
            )

            # Zadania
            scheduled_ids = {i.get("task_id") for i in items if i.get("type") == "task"}
            original_ids = {str(t.id) for t in tasks if not t.completed}
            unsch = len(original_ids - scheduled_ids)

            # Bilans czasu
            total_productive = total_task + total_activity
            total_personal = total_meal + total_routine
            total_rest = total_break + total_sleep

            # Kompletny zestaw metryk
            metric = {
                "total_task_minutes": total_task,
                "total_break_minutes": total_break,
                "total_fixed_minutes": total_fixed,
                "total_sleep_minutes": total_sleep,
                "total_meal_minutes": total_meal,
                "total_routine_minutes": total_routine,
                "total_activity_minutes": total_activity,
                "total_productive_minutes": total_productive,
                "total_personal_minutes": total_personal,
                "total_rest_minutes": total_rest,
                "unscheduled_tasks": unsch,
                "task_completion_pct": (
                    (len(scheduled_ids) / len(original_ids) * 100)
                    if original_ids
                    else 100.0
                ),
                "work_life_balance": round(total_personal / max(1, total_productive) * 100, 1),
            }
            logger.info(f"Calculated metrics: {metric}")
            return metric
        except Exception:
            logger.exception("Błąd obliczania metryk.")
            return {"status": "error"}

    def _create_empty(
        self,
        input_data: ScheduleInputData,
        warnings: List[str],
        error_msg: str,
    ) -> GeneratedSchedule:
        """
        Tworzy pusty harmonogram w przypadku błędu.

        Args:
            input_data: Dane wejściowe.
            warnings: Lista ostrzeżeń.
            error_msg: Powód niepowodzenia.

        Returns:
            GeneratedSchedule z pustymi danymi.
        """
        logger.error(f"Generuję pusty harmonogram: {error_msg}")
        return GeneratedSchedule(
            user_id=input_data.user_id,
            target_date=input_data.target_date,
            scheduled_items=[],
            metrics={"status": "failed"},
            explanations={"error": error_msg},
            warnings=warnings + [error_msg],
        )


# --- Przykład użycia ---
async def run_example():  # pragma: no cover
    """
    Zaawansowany przykład ilustrujący wykorzystanie Scheduler.
    """
    # Konfiguracja loggingu
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Ładowanie konfiguracji z pliku
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(script_dir, '..', '..', 'data', 'config', 'default.yaml')
    try:
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f)
    except Exception:
        logger.warning(f"Nie można wczytać configu z {cfg_path}, używam domyślnych.")
        cfg = {}

    # Inicjalizacja komponentów
    sleep_calc = SleepCalculator(config=cfg.get('sleep', {}))
    chrono_an = ChronotypeAnalyzer(config=cfg.get('chronotype', {}))
    prio_cfg = cfg.get('task_prioritizer', {})
    task_prio = TaskPrioritizer(
        weights=prio_cfg.get('weights'),
        user_energy_pattern=prio_cfg.get('default_user_energy_pattern'),
    )
    solver = ConstraintSchedulerSolver(config=cfg.get('solver', {}))
    llm = None
    if cfg.get('llm', {}).get('enabled'):
        try:
            llm = LLMEngine(config=cfg.get('llm', {}))
        except Exception:
            logger.warning("LLM Engine nie zainicjalizowany, pomijam dopieszczanie LLM.")

    # Przygotowanie przykładowych zadań - zadania po pracy, ponieważ praca jest niepodzielnym blokiem
    from uuid import uuid4
    user_id = uuid4()
    tgt_date = date.today() + timedelta(days=1)
    task1 = Task(
        id=uuid4(),
        title="Przygotuj raport kwartalny",
        duration=timedelta(hours=1, minutes=30),
        priority=TaskPriority.HIGH,
        energy_level=EnergyLevel.MEDIUM,
        # Zadanie po pracy
        earliest_start=time(16, 30),
        deadline=datetime.combine(tgt_date, time(21, 0), tzinfo=timezone.utc),
    )
    task2 = Task(
        id=uuid4(),
        title="Spotkanie z przyjacielem",
        duration=timedelta(minutes=45),
        priority=TaskPriority.MEDIUM,
        energy_level=EnergyLevel.LOW,
        # Zadanie po pracy
        earliest_start=time(18, 0),
    )
    # Parser dla stringowych durations z manualnym parsowaniem H:MM
    duration_str = "1:00"
    try:
        hours_str, mins_str = duration_str.split(":")
        dur3 = timedelta(hours=int(hours_str), minutes=int(mins_str))
    except Exception:
        raise ValueError(f"Niepoprawny format czasu trwania dla zadania 'Czytanie książki': {duration_str}")
    task3 = Task(
        id=uuid4(),
        title="Czytanie książki",
        duration=dur3,
        priority=TaskPriority.LOW,
        energy_level=EnergyLevel.MEDIUM,
        # Zadanie wieczorem
        earliest_start=time(20, 0),
    )
    tasks = [task1, task2, task3]

    # Wydarzenia stałe - praca jako fixed event, niepodzielny blok
    fixed = [
        {"id": "praca", "start_time": "08:00", "end_time": "16:00"},  # Typowy dzień pracy 8-16 jako niepodzielny blok
        {"id": "dojazd_do_pracy", "start_time": "07:40", "end_time": "08:00"},  # Dojazd do pracy (20 min)
        {"id": "dojazd_z_pracy", "start_time": "16:00", "end_time": "16:20"},  # Dojazd z pracy (20 min)
    ]

    # Informacje o pracy
    work_info = {
        "hours": {"start": "08:00", "end": "16:00"},
        "type": "stacjonarna",  # stacjonarna/hybrydowa/zdalna
        "commute_time_minutes": 20,
        "location": "Biuro w centrum miasta"
    }

    # Preferencje użytkownika (z dodanymi activity_goals)
    prefs = {
        "preferred_wake_time": "06:30",
        "sleep_need_scale": 60,
        "chronotype_scale": 40,
        "work_info": work_info,  # Dodajemy informacje o pracy do preferencji
        "meals": { # Example meal preferences
            "breakfast_time": "07:00", "duration_minutes": 20,
            "lunch_time": "16:30", "duration_minutes": 45,  # Obiad po pracy
            "dinner_time": "19:30", "duration_minutes": 30,
        },
        "routines": { # Example routine preferences
             "morning_duration_minutes": 30,
             "evening_duration_minutes": 45,
        },
        "activity_goals": [ # Example activity goals
            {
                "name": "Gym Workout",
                "duration_minutes": 60,
                "frequency": "Mon,Wed,Fri",
                "preferred_time": ["evening"]
            },
            {
                "name": "Reading",
                "duration_minutes": 30,
                "frequency": "daily",
                "preferred_time": ["evening", "before_sleep"]
            }
        ]
    }

    # Przykładowe dane z urządzeń wearable
    wearable_data = {
        "sleep_quality": "Good",
        "stress_level": "Low",
        "readiness_score": 0.85,
        "steps_yesterday": 8500,
        "avg_heart_rate": 68,
        "sleep_duration_hours": 7.5,
        "deep_sleep_percentage": 22,
        "rem_sleep_percentage": 18
    }

    # Przykładowe dane historyczne
    historical_data = {
        "typical_lunch_time": "13:05",
        "common_activity": "Evening walk around 18:00",
        "task_completion_ratio": 1.1,
        "productive_hours": ["09:00-12:00", "15:00-17:00"],
        "common_breaks": ["10:30", "15:30"],
        "typical_sleep_duration": 7.5
    }

    input_data = ScheduleInputData(
        user_id=user_id,
        target_date=tgt_date,
        tasks=tasks,
        fixed_events_input=fixed,
        preferences=prefs,
        user_profile_data={"age": 30, "meq_score": 55, "name": "Jan Kowalski"},
        wearable_data_today=wearable_data,
        historical_data=historical_data
    )

    sched = Scheduler(
        sleep_calculator=sleep_calc,
        chronotype_analyzer=chrono_an,
        task_prioritizer=task_prio,
        constraint_solver=solver,
        llm_engine=llm, # Pass the instantiated LLM engine
        # Assuming wearable_service and history_service would be injected here in a real app
        wearable_service=None, # Using None for example as placeholders handle it
        history_service=None,  # Using None for example as placeholders handle it
        config=cfg.get('scheduler', {}),
    )
    # Ensure LLM refinement is attempted if llm engine is available
    sched._llm_refinement_enabled = llm is not None
    logger.info(f"LLM Refinement explicitly set to: {sched._llm_refinement_enabled}")

    # Generowanie harmonogramu
    print("Generuję harmonogram...")
    result = await sched.generate_schedule(input_data)

    # Wyświetlenie danych wejściowych w czytelnej formie
    print("\n" + "="*80)
    print("DANE WEJŚCIOWE UŻYTE DO GENEROWANIA HARMONOGRAMU".center(80))
    print("="*80)

    print(f"\n📅 Data: {input_data.target_date.strftime('%d.%m.%Y (%A)')}")
    print(f"👤 Użytkownik: ID {input_data.user_id}")

    # Dane profilu użytkownika
    print("\n📊 PROFIL UŻYTKOWNIKA:")
    profile_data = input_data.user_profile_data or {}
    print(f"   • Wiek: {profile_data.get('age', 'Nie określono')}")
    print(f"   • Wynik MEQ (chronotyp): {profile_data.get('meq_score', 'Nie określono')}")

    # Preferencje
    print("\n⚙️ PREFERENCJE UŻYTKOWNIKA:")
    if input_data.preferences:
        print(f"   • Preferowana godzina pobudki: {input_data.preferences.get('preferred_wake_time', 'Nie określono')}")
        print(f"   • Skala potrzeby snu (0-100): {input_data.preferences.get('sleep_need_scale', 'Nie określono')}")
        print(f"   • Skala chronotypu (0-100): {input_data.preferences.get('chronotype_scale', 'Nie określono')}")

        # Informacje o pracy
        work_info = input_data.preferences.get('work_info', {})
        if work_info:
            print("\n💼 INFORMACJE O PRACY:")
            work_hours = work_info.get('hours', {})
            if work_hours:
                print(f"   • Godziny pracy: {work_hours.get('start', 'Nie określono')} - {work_hours.get('end', 'Nie określono')}")
            print(f"   • Typ pracy: {work_info.get('type', 'Nie określono')}")
            print(f"   • Czas dojazdu: {work_info.get('commute_time_minutes', 'Nie określono')} min")
            print(f"   • Lokalizacja: {work_info.get('location', 'Nie określono')}")

        # Preferencje posiłków
        meal_prefs = input_data.preferences.get('meals', {})
        if meal_prefs:
            print("\n🍽️ PREFERENCJE POSIŁKÓW:")
            print(f"   • Śniadanie: {meal_prefs.get('breakfast_time', 'Nie określono')} (czas trwania: {meal_prefs.get('duration_minutes', 'Nie określono')} min)")
            print(f"   • Obiad: {meal_prefs.get('lunch_time', 'Nie określono')} (czas trwania: {meal_prefs.get('duration_minutes', 'Nie określono')} min)")
            print(f"   • Kolacja: {meal_prefs.get('dinner_time', 'Nie określono')} (czas trwania: {meal_prefs.get('duration_minutes', 'Nie określono')} min)")

        # Preferencje rutyn
        routine_prefs = input_data.preferences.get('routines', {})
        if routine_prefs:
            print("\n🔄 PREFERENCJE RUTYN:")
            print(f"   • Rutyna poranna: {routine_prefs.get('morning_duration_minutes', 'Nie określono')} min")
            print(f"   • Rutyna wieczorna: {routine_prefs.get('evening_duration_minutes', 'Nie określono')} min")

        # Cele aktywności
        activity_goals = input_data.preferences.get('activity_goals', [])
        if activity_goals:
            print("\n🏃 CELE AKTYWNOŚCI:")
            for i, goal in enumerate(activity_goals, 1):
                print(f"   {i}. {goal.get('name', 'Aktywność')}:")
                print(f"      - Czas trwania: {goal.get('duration_minutes', 'Nie określono')} min")
                print(f"      - Częstotliwość: {goal.get('frequency', 'Nie określono')}")
                print(f"      - Preferowany czas: {', '.join(goal.get('preferred_time', ['Nie określono']))}")
    else:
        print("   Brak zdefiniowanych preferencji.")

    # Zadania
    print("\n📝 ZADANIA DO ZAPLANOWANIA:")
    if input_data.tasks:
        for i, task in enumerate(input_data.tasks, 1):
            print(f"   {i}. {task.title}:")
            print(f"      - Czas trwania: {task.duration}")
            print(f"      - Priorytet: {task.priority.name}")
            print(f"      - Poziom energii: {task.energy_level.name}")
            if task.deadline:
                print(f"      - Deadline: {task.deadline.strftime('%d.%m.%Y %H:%M')}")
            if task.earliest_start:
                print(f"      - Najwcześniejszy start: {task.earliest_start}")
    else:
        print("   Brak zadań do zaplanowania.")

    # Wydarzenia stałe
    print("\n📌 WYDARZENIA STAŁE:")
    if input_data.fixed_events_input:
        for i, event in enumerate(input_data.fixed_events_input, 1):
            print(f"   {i}. {event.get('id', 'Wydarzenie')}:")
            print(f"      - Czas: {event.get('start_time', 'Nie określono')} - {event.get('end_time', 'Nie określono')}")
    else:
        print("   Brak wydarzeń stałych.")

    # Dane z urządzeń wearable
    print("\n⌚ DANE Z URZĄDZEŃ WEARABLE:")
    if input_data.wearable_data_today:
        for key, value in input_data.wearable_data_today.items():
            print(f"   • {key}: {value}")
    else:
        print("   Brak danych z urządzeń wearable.")

    # Dane historyczne
    print("\n📊 DANE HISTORYCZNE:")
    if input_data.historical_data:
        for key, value in input_data.historical_data.items():
            print(f"   • {key}: {value}")
    else:
        print("   Brak danych historycznych.")

    # Wyświetlenie wyników
    print("\n" + "="*80)
    print("WYGENEROWANY HARMONOGRAM".center(80))
    print("="*80 + "\n")

    print(f"📅 Harmonogram na {result.target_date.strftime('%d.%m.%Y (%A)')} (ID: {result.schedule_id})")
    print("\nGodzina      | Aktywność" + " "*40 + "| Typ")
    print("-"*80)
    for item in result.scheduled_items:
        activity_name = item['name']
        activity_type = item['type']
        time_slot = f"{item['start_time']} - {item['end_time']}"
        print(f"{time_slot:12} | {activity_name:48} | {activity_type}")

    # Wyświetlenie metryk
    print("\n📊 METRYKI HARMONOGRAMU:")
    metrics = result.metrics
    if metrics:
        print(f"   • Czas zadań: {metrics.get('total_task_minutes', 0)} min")
        print(f"   • Czas przerw: {metrics.get('total_break_minutes', 0)} min")
        print(f"   • Czas wydarzeń stałych: {metrics.get('total_fixed_minutes', 0)} min")
        print(f"   • Czas snu: {metrics.get('total_sleep_minutes', 0)} min")
        print(f"   • Czas posiłków: {metrics.get('total_meal_minutes', 0)} min")
        print(f"   • Czas rutyn: {metrics.get('total_routine_minutes', 0)} min")
        print(f"   • Czas aktywności: {metrics.get('total_activity_minutes', 0)} min")
        print(f"   • Czas produktywny: {metrics.get('total_productive_minutes', 0)} min")
        print(f"   • Czas osobisty: {metrics.get('total_personal_minutes', 0)} min")
        print(f"   • Czas odpoczynku: {metrics.get('total_rest_minutes', 0)} min")
        print(f"   • Niezaplanowane zadania: {metrics.get('unscheduled_tasks', 0)}")
        print(f"   • Procent ukończenia zadań: {metrics.get('task_completion_pct', 0)}%")
        print(f"   • Balans praca-życie: {metrics.get('work_life_balance', 0)}%")

    # Wyświetlenie ostrzeżeń
    if result.warnings:
        print("\n⚠️ OSTRZEŻENIA:")
        for warning in result.warnings:
            print(f"   • {warning}")
    else:
        print("\n✅ Brak ostrzeżeń.")

    # Zwracamy wynik, aby móc go wykorzystać w innych funkcjach
    return result


def save_schedule_to_json(schedule_result, file_path):
    """
    Zapisuje wygenerowany harmonogram do pliku JSON w formacie kompatybilnym z APIdog.

    Args:
        schedule_result: Wynik generowania harmonogramu.
        file_path: Ścieżka do pliku, w którym zostanie zapisany harmonogram.
    """
    import json
    import os

    # Konwersja harmonogramu do formatu APIdog
    tasks = []
    for item in schedule_result.scheduled_items:
        tasks.append({
            "start_time": item['start_time'],
            "end_time": item['end_time'],
            "task": item['name']
        })

    # Tworzenie struktury JSON
    schedule_json = {
        "tasks": tasks
    }

    # Upewnienie się, że katalog istnieje
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Zapisanie do pliku
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(schedule_json, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Harmonogram zapisany w pliku: {file_path}")


async def run_example_and_save():
    """
    Uruchamia przykład generowania harmonogramu i zapisuje wynik do pliku JSON.
    """
    result = await run_example()

    # Zapisanie harmonogramu do pliku JSON
    import os
    file_path = os.path.join('data', 'processed', f"schedule_{result.schedule_id}.json")
    save_schedule_to_json(result, file_path)

    return result


if __name__ == '__main__':
    import asyncio

    asyncio.run(run_example_and_save())
