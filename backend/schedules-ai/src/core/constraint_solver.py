# === File: scheduler-core/src/core/constraint_solver.py ===

"""
Constraint Satisfaction Programming (CSP) Solver for Scheduling using OR-Tools.

Leverages Google OR-Tools CP-SAT solver to find optimal or feasible schedules
based on tasks, fixed events, user preferences, energy patterns, and various
constraints like dependencies and non-overlapping requirements.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, time
from typing import Any, Dict, List, Optional
from uuid import UUID

# Third-party imports
try:
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
except ImportError:
    logging.getLogger(__name__).warning(
        "Google OR-Tools (ortools) library not found. "
        "ConstraintSchedulerSolver will not function. "
        "Install with: poetry add ortools"
    )
    ORTOOLS_AVAILABLE = False

# Application-specific imports (absolute paths)
try:
    from src.core.task_prioritizer import EnergyLevel, TaskPriority
except ImportError:
    from enum import Enum
    class TaskPriority(Enum):
        HIGH = 4; MEDIUM = 3; LOW = 2; VERY_LOW = 1  # type: ignore
    class EnergyLevel(Enum):
        HIGH = 3; MEDIUM = 2; LOW = 1  # type: ignore
    logging.getLogger(__name__).warning("Could not import TaskPriority/EnergyLevel enums.")

try:
    from src.utils.time_utils import time_to_total_minutes, total_minutes_to_time
    TIME_UTILS_AVAILABLE = True
except ImportError:
    logging.getLogger(__name__).warning("Could not import time helpers from src.utils. Defining locally (may cause issues).")
    TIME_UTILS_AVAILABLE = False
    def time_to_total_minutes(t: time) -> int:
        return t.hour * 60 + t.minute
    def total_minutes_to_time(total_minutes: int) -> time:
        total_minutes = max(0, min(1439, int(total_minutes)))  # Clamp to 0-1439
        hours, minutes = divmod(total_minutes, 60)
        return time(hour=hours % 24, minute=minutes)


logger = logging.getLogger(__name__)


# --- Solver-Specific Data Structures ---

@dataclass(frozen=True)
class FixedEventInterval:
    """Represents a fixed, immovable time interval for the solver."""
    id: str  # Unique identifier (e.g., "lunch", "meeting-xyz")
    start_minutes: int  # Minutes from day start (0-1439)
    end_minutes: int    # Minutes from day start (0-1439)

    def __post_init__(self):
        if not (0 <= self.start_minutes <= 1439 and 0 <= self.end_minutes <= 1440):
            raise ValueError("FixedEventInterval minutes must be within a day (0-1440).")
        if self.end_minutes <= self.start_minutes:
            raise ValueError("FixedEventInterval end_minutes must be after start_minutes.")
        if (self.end_minutes - self.start_minutes) <= 0:
            raise ValueError("FixedEventInterval must have a positive duration.")


@dataclass(frozen=True)
class SolverTask:
    """Internal representation of a task optimized for the CP-SAT solver."""
    id: UUID
    duration_minutes: int  # Task duration in minutes
    priority: int = 3      # Numerical priority (higher is more important)
    energy_level: int = 2  # Numerical energy level required (e.g., 1=Low, 2=Med, 3=High)
    earliest_start_minutes: Optional[int] = None  # Optional constraint: Earliest start (minutes from day start)
    latest_end_minutes: Optional[int] = None      # Optional constraint: Latest end (minutes from day start)
    dependencies: List[UUID] = field(default_factory=list)  # List of task IDs this task depends on

    def __post_init__(self):
        if self.duration_minutes <= 0:
            raise ValueError(f"SolverTask duration must be positive (got {self.duration_minutes} for task {self.id}).")
        if self.earliest_start_minutes is not None and self.earliest_start_minutes < 0:
            raise ValueError(f"SolverTask earliest_start_minutes cannot be negative (got {self.earliest_start_minutes} for task {self.id}).")
        if self.latest_end_minutes is not None and self.latest_end_minutes > 1440:
            raise ValueError(f"SolverTask latest_end_minutes cannot exceed 1440 (got {self.latest_end_minutes} for task {self.id}).")
        if self.earliest_start_minutes is not None and self.latest_end_minutes is not None:
            if self.latest_end_minutes < self.earliest_start_minutes + self.duration_minutes:
                raise ValueError(f"SolverTask constraints impossible: latest_end ({self.latest_end_minutes}) < earliest_start ({self.earliest_start_minutes}) + duration ({self.duration_minutes}) for task {self.id}.")


@dataclass(frozen=True)
class SolverInput:
    """Input data bundle for the constraint solver."""
    target_date: date
    tasks: List[SolverTask]
    fixed_events: List[FixedEventInterval]
    day_start_minutes: int = 0   # Default: Start of the day
    day_end_minutes: int = 1440  # Default: End of the day (24 * 60)
    user_energy_pattern: Dict[int, float] = field(default_factory=dict)

    def __post_init__(self):
        if not (0 <= self.day_start_minutes < self.day_end_minutes <= 1440):
            raise ValueError("Invalid day start/end minutes. Must be 0 <= start < end <= 1440.")
        if not self.tasks:
            logger.warning("SolverInput created with no tasks to schedule.")
        for hour in self.user_energy_pattern:
            if not (0 <= hour <= 23):
                raise ValueError(f"Invalid hour key '{hour}' in user_energy_pattern. Must be 0-23.")


@dataclass(frozen=True)
class ScheduledTaskInfo:
    """Output structure representing a single scheduled task."""
    task_id: UUID
    start_time: time  # Local time on the target date
    end_time: time    # Local time on the target date
    task_date: date   # The date the task is scheduled for


# --- Solver Class ---

class ConstraintSchedulerSolver:
    """
    Uses Google OR-Tools CP-SAT solver to find an optimal or feasible schedule
    based on the provided SolverInput.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initializes the ConstraintSchedulerSolver.

        Args:
            config (Optional[Dict[str, Any]]): Configuration dictionary, potentially
                containing:
                - solver_time_limit_seconds (float): Max time for the solver.
                - objective_weights (Dict[str, int]): Weights for different objective terms.
        """
        if not ORTOOLS_AVAILABLE:
            logger.error("OR-Tools library is not available. Solver cannot function.")
        if not TIME_UTILS_AVAILABLE:
            logger.warning("Time utility functions not imported. Time conversions might be inaccurate.")

        self._config = config or {}
        self._solver_time_limit_seconds: float = float(self._config.get("solver_time_limit_seconds", 30.0))
        default_objective_weights = {"priority": 10, "energy_match": 5, "start_time_penalty": 1}
        config_objective_weights = self._config.get("objective_weights", {})
        merged_weights = default_objective_weights.copy()
        for key, value in config_objective_weights.items():
            if isinstance(value, (int, float)):
                merged_weights[key] = int(value)
            else:
                logger.warning(f"Ignoring non-numeric objective weight '{key}' from config: {value}")
        self._objective_weights: Dict[str, int] = merged_weights

        logger.info(
            f"ConstraintSchedulerSolver initialized (OR-Tools Available: {ORTOOLS_AVAILABLE}). "
            f"Time limit: {self._solver_time_limit_seconds}s, Objective Weights: {self._objective_weights}"
        )

    def solve(self, solver_input: SolverInput) -> Optional[List[ScheduledTaskInfo]]:
        """
        Attempts to find an optimal schedule using the CP-SAT solver.

        Args:
            solver_input (SolverInput): The structured input data containing tasks,
                                        fixed events, and constraints.

        Returns:
            Optional[List[ScheduledTaskInfo]]: A list of scheduled task details,
                sorted by start time, if a solution is found. Returns None if
                OR-Tools is unavailable, input is invalid, or no solution is found.
        """
        if not ORTOOLS_AVAILABLE:
            logger.error("Cannot solve: OR-Tools library is not available.")
            return None
        if not isinstance(solver_input, SolverInput):
            logger.error("Invalid solver_input type provided.")
            return None
        if not solver_input.tasks:
            logger.warning("No tasks provided in solver_input. Returning empty schedule.")
            return []

        model = cp_model.CpModel()
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self._solver_time_limit_seconds

        tasks = solver_input.tasks
        task_map = {task.id: task for task in tasks}
        horizon = solver_input.day_end_minutes

        # --- 1. Create Interval Variables for Tasks ---
        task_intervals: Dict[UUID, cp_model.IntervalVar] = {}
        task_starts: Dict[UUID, cp_model.IntVar] = {}
        task_ends: Dict[UUID, cp_model.IntVar] = {}

        logger.debug(f"Creating variables for {len(tasks)} tasks within horizon {solver_input.day_start_minutes}-{horizon}.")
        for task in tasks:
            try:
                earliest_possible_start = max(solver_input.day_start_minutes, task.earliest_start_minutes or 0)
                latest_possible_end = min(horizon, task.latest_end_minutes or horizon)
                latest_possible_start = latest_possible_end - task.duration_minutes
                earliest_possible_end = earliest_possible_start + task.duration_minutes

                if earliest_possible_start > latest_possible_start:
                    logger.error(f"Task {task.id} is impossible to schedule due to time constraints/duration.")
                    continue

                start_var = model.NewIntVar(earliest_possible_start, latest_possible_start, f'start_{task.id}')
                end_var = model.NewIntVar(earliest_possible_end, latest_possible_end, f'end_{task.id}')
                # Create IntervalVar with required four arguments: start, duration, end, and name.
                interval_var = model.NewIntervalVar(start_var, task.duration_minutes, end_var, f'interval_{task.id}')

                task_intervals[task.id] = interval_var
                task_starts[task.id] = start_var
                task_ends[task.id] = end_var

            except Exception as e:
                logger.exception(f"Error creating variables for task {task.id}")
                return None

        if not task_intervals:
            logger.warning("No valid task variables were created. Cannot solve.")
            return []

        # --- 2. Add Constraints ---
        logger.debug("Adding constraints...")
        try:
            model.AddNoOverlap(list(task_intervals.values()))

            fixed_event_intervals: List[cp_model.IntervalVar] = []
            for event in solver_input.fixed_events:
                event_start = max(solver_input.day_start_minutes, event.start_minutes)
                event_end = min(horizon, event.end_minutes)
                event_duration = event_end - event_start
                if event_duration > 0:
                    fixed_interval = model.NewFixedSizeIntervalVar(event_start, event_duration, f'fixed_{event.id}')
                    fixed_event_intervals.append(fixed_interval)
                else:
                    logger.debug(f"Skipping fixed event '{event.id}' outside or zero duration within horizon.")

            if fixed_event_intervals:
                model.AddNoOverlap(list(task_intervals.values()) + fixed_event_intervals)

            for task_id, task in task_map.items():
                if task_id not in task_starts:
                    continue
                for dep_id in task.dependencies:
                    if dep_id in task_ends:
                        model.Add(task_starts[task_id] >= task_ends[dep_id])
                        logger.debug(f"Added dependency: Task {str(task_id)[:8]} >= Task {str(dep_id)[:8]}")
                    else:
                        logger.warning(f"Dependency task ID '{dep_id}' for task '{task_id}' not found or invalid. Skipping dependency.")

        except Exception as e:
            logger.exception("Error adding constraints to the model.")
            return None

        # --- 3. Define Objective Function ---
        logger.debug("Defining objective function...")
        objective_terms = []
        try:
            priority_weight = self._objective_weights.get("priority", 10)
            energy_weight = self._objective_weights.get("energy_match", 5)
            start_penalty_weight = self._objective_weights.get("start_time_penalty", 1)

            hourly_energy_scores: Dict[int, Dict[int, int]] = {}
            for task_energy_level in range(1, 4):
                task_energy_norm = task_energy_level / 3.0
                hourly_scores: Dict[int, int] = {}
                for hour in range(24):
                    user_energy = solver_input.user_energy_pattern.get(hour, 0.5)
                    match = 1.0 - abs(user_energy - task_energy_norm)
                    hourly_scores[hour] = int(match * 100)
                hourly_energy_scores[task_energy_level] = hourly_scores

            for task_id, task in task_map.items():
                if task_id not in task_intervals:
                    continue

                objective_terms.append(model.NewConstant(task.priority * priority_weight))
                objective_terms.append(task_starts[task_id] * -start_penalty_weight)

                if energy_weight > 0 and task.energy_level in hourly_energy_scores:
                    scores_for_task = [hourly_energy_scores[task.energy_level][h] for h in range(24)]
                    start_hour_var = model.NewIntVar(0, 23, f'start_hour_{task_id}')
                    model.AddDivisionEquality(start_hour_var, task_starts[task_id], 60)
                    energy_score_var = model.NewIntVar(0, 100, f'energy_score_{task_id}')
                    model.AddElement(start_hour_var, scores_for_task, energy_score_var)
                    objective_terms.append(energy_score_var * energy_weight)

            model.Maximize(sum(objective_terms))
            logger.debug("Objective function defined.")

        except Exception as e:
            logger.exception("Error defining the objective function.")
            return None

        # --- 4. Solve the Model ---
        logger.info(f"Starting CP-SAT solver with time limit: {self._solver_time_limit_seconds}s...")
        status = solver.Solve(model)
        status_name = solver.StatusName(status)
        logger.info(f"Solver finished. Status: {status_name}")
        logger.info(f"Objective value: {solver.ObjectiveValue()}")
        logger.info(f"Wall time: {solver.WallTime()}s")

        # --- 5. Process Solution ---
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            schedule: List[ScheduledTaskInfo] = []
            processed_task_ids = set()
            for task_id, interval_var in task_intervals.items():
                try:
                    start_val = solver.Value(task_starts[task_id])
                    end_val = solver.Value(task_ends[task_id])
                    start_time = total_minutes_to_time(start_val)
                    end_time = total_minutes_to_time(end_val)
                    schedule.append(
                        ScheduledTaskInfo(
                            task_id=task_id,
                            start_time=start_time,
                            end_time=end_time,
                            task_date=solver_input.target_date
                        )
                    )
                    processed_task_ids.add(task_id)
                except Exception as e:
                    logger.error(f"Error processing solution for task {task_id}: {e}")
            if len(processed_task_ids) != len(task_intervals):
                logger.warning(f"Solver found a solution, but only {len(processed_task_ids)} out of {len(task_intervals)} tasks could be placed.")
            schedule.sort(key=lambda x: x.start_time)
            logger.info(f"Found solution with {len(schedule)} scheduled tasks.")
            return schedule
        else:
            logger.warning(f"Solver did not find an optimal or feasible solution (Status: {status_name}).")
            return None


# --- Module-level Example Usage ---

def run_example():
    """Runs an example demonstrating the ConstraintSchedulerSolver."""
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 1. Define Tasks
    task1_id = UUID('a0000001-e89b-12d3-a456-426614174000')
    task2_id = UUID('a0000002-e89b-12d3-a456-426614174000')
    task3_id = UUID('a0000003-e89b-12d3-a456-426614174000')
    task4_id = UUID('a0000004-e89b-12d3-a456-426614174000')

    solver_tasks = [
        SolverTask(id=task1_id, duration_minutes=120, priority=TaskPriority.HIGH.value, energy_level=EnergyLevel.HIGH.value),
        SolverTask(id=task2_id, duration_minutes=45, priority=TaskPriority.MEDIUM.value, energy_level=EnergyLevel.MEDIUM.value, dependencies=[task1_id]),
        SolverTask(id=task3_id, duration_minutes=60, priority=TaskPriority.HIGH.value, energy_level=EnergyLevel.LOW.value),
        SolverTask(id=task4_id, duration_minutes=30, priority=TaskPriority.LOW.value, energy_level=EnergyLevel.MEDIUM.value, earliest_start_minutes=time_to_total_minutes(time(16, 30))),
    ]

    # 2. Define Fixed Events
    today = date.today()
    fixed_events = [
        FixedEventInterval(id="lunch", start_minutes=time_to_total_minutes(time(12, 30)), end_minutes=time_to_total_minutes(time(13, 15))),
        FixedEventInterval(id="meeting", start_minutes=time_to_total_minutes(time(15, 0)), end_minutes=time_to_total_minutes(time(16, 0))),
    ]

    # 3. Define User Energy Pattern (Normalized 0.0-1.0)
    energy_pattern = {h: 0.5 for h in range(24)}
    energy_pattern.update({
        8: 0.7, 9: 0.8, 10: 0.9, 11: 0.8,
        12: 0.6, 13: 0.5,
        14: 0.7, 15: 0.6,
        16: 0.5, 17: 0.4
    })

    # 4. Create Solver Input
    solver_input = SolverInput(
        target_date=today,
        tasks=solver_tasks,
        fixed_events=fixed_events,
        day_start_minutes=time_to_total_minutes(time(8, 0)),  # 8:00 AM
        day_end_minutes=time_to_total_minutes(time(18, 0)),   # 6:00 PM
        user_energy_pattern=energy_pattern
    )

    # 5. Initialize and Run Solver
    solver = ConstraintSchedulerSolver(config={"solver_time_limit_seconds": 10.0})
    solution = solver.solve(solver_input)

    # 6. Print Results
    print("\n--- Solver Results ---")
    if solution:
        print(f"Optimal schedule found for {solver_input.target_date}:")
        print("  Fixed Events:")
        for event in fixed_events:
            start_t = total_minutes_to_time(event.start_minutes)
            end_t = total_minutes_to_time(event.end_minutes)
            print(f"    {start_t.strftime('%H:%M')} - {end_t.strftime('%H:%M')}: {event.id}")
        print("  Scheduled Tasks:")
        for item in solution:
            task_info = next((t for t in solver_tasks if t.id == item.task_id), None)
            prio = task_info.priority if task_info else '?'
            energy = task_info.energy_level if task_info else '?'
            deps = task_info.dependencies if task_info else []
            dep_str = f" (Deps: {', '.join(str(d)[:4] for d in deps)})" if deps else ""
            print(f"    {item.start_time.strftime('%H:%M')} - {item.end_time.strftime('%H:%M')}: "
                  f"Task {str(item.task_id)[:4]}... (Prio: {prio}, Energy: {energy}){dep_str}")
    else:
        print("No solution found.")


if __name__ == "__main__":
    run_example()
