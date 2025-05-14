# === File: scheduler-core/src/core/task_prioritizer.py ===

"""
Task Definition and Prioritization Module.

Defines the structure for tasks within the system and provides logic for
calculating task priority based on factors like explicit priority level,
deadlines, dependencies, and historical data (e.g., postponements).
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


# --- Enums ---

class TaskPriority(Enum):
    """Enumeration of task priority levels."""
    CRITICAL = 5    # Must be done today/ASAP, often time-sensitive.
    HIGH = 4        # Important, should be done soon.
    MEDIUM = 3      # Standard priority, default.
    LOW = 2         # Less important, can be deferred if needed.
    OPTIONAL = 1    # Nice to have, can be easily postponed.

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class EnergyLevel(Enum):
    """Enumeration of estimated energy level required for a task."""
    HIGH = 3        # Requires significant mental focus or physical exertion.
    MEDIUM = 2      # Requires moderate focus or effort.
    LOW = 1         # Can be done with low energy or during breaks.


# --- Task Data Structure ---

@dataclass
class Task:
    """
    Represents a single task to be scheduled or managed.

    Attributes:
        title: Short, descriptive title of the task.
        id: Unique identifier for the task.
        description: Optional longer description or notes.
        priority: Explicit priority level assigned to the task.
        energy_level: Estimated energy required to perform the task.
        duration: Estimated time required to complete the task.
        deadline: Optional date or datetime by which the task must be completed.
        earliest_start: Optional date or datetime before which the task cannot start.
        dependencies: Set of IDs of tasks that must be completed before this one can start.
        tags: List of keywords or categories for organization.
        location: Optional context or location required (e.g., "at_computer", "office").
        completed: Boolean flag indicating if the task is done.
        completion_date: Timestamp when the task was marked complete.
        postponed_count: Number of times the task has been deferred or rescheduled.
        created_at: Timestamp when the task was created.
        last_modified: Timestamp when the task was last modified.
    """
    # Mandatory field(s) without defaults first.
    title: str

    # Fields with default values
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    energy_level: EnergyLevel = EnergyLevel.MEDIUM
    duration: timedelta = timedelta(minutes=30)
    deadline: Optional[datetime] = None
    earliest_start: Optional[datetime] = None
    dependencies: Set[UUID] = field(default_factory=set)
    tags: List[str] = field(default_factory=list)
    location: Optional[str] = None
    completed: bool = False
    completion_date: Optional[datetime] = None
    postponed_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if not self.title:
            raise ValueError("Task title cannot be empty.")
        if self.duration.total_seconds() <= 0:
            raise ValueError(f"Task duration must be positive (got {self.duration} for '{self.title}').")
        if self.deadline and self.deadline.tzinfo is None:
            logger.warning(f"Task '{self.title}' deadline is timezone-naive. Assuming UTC.")
            object.__setattr__(self, 'deadline', self.deadline.replace(tzinfo=timezone.utc))
        if self.earliest_start and self.earliest_start.tzinfo is None:
            logger.warning(f"Task '{self.title}' earliest_start is timezone-naive. Assuming UTC.")
            object.__setattr__(self, 'earliest_start', self.earliest_start.replace(tzinfo=timezone.utc))
        if self.completion_date and self.completion_date.tzinfo is None:
            logger.warning(f"Task '{self.title}' completion_date is timezone-naive. Assuming UTC.")
            object.__setattr__(self, 'completion_date', self.completion_date.replace(tzinfo=timezone.utc))

    def __hash__(self) -> int:
        """Make Task hashable based on its unique ID."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Compare Tasks based on their unique IDs."""
        if not isinstance(other, Task):
            return NotImplemented
        return self.id == other.id

    def mark_complete(self) -> None:
        """Marks the task as complete with the current UTC timestamp."""
        if not self.completed:
            now_utc = datetime.now(timezone.utc)
            self.completed = True
            self.completion_date = now_utc
            self.last_modified = now_utc
            logger.info(f"Task '{self.title}' ({self.id}) marked as complete at {now_utc}.")

    def time_urgency_factor(self, current_datetime: Optional[datetime] = None) -> float:
        """
        Calculates an urgency factor (0.0 to 1.0) based on deadline proximity.

        Higher values indicate greater urgency. Returns 0.0 if no deadline.
        Uses an exponential curve, increasing urgency faster as the deadline nears.

        Args:
            current_datetime (Optional[datetime]): The reference time for calculation.
                                                   Defaults to datetime.now(timezone.utc).

        Returns:
            float: Urgency factor between 0.0 and 1.0.
        """
        if not self.deadline:
            return 0.0

        now = current_datetime or datetime.now(timezone.utc)

        if self.deadline.tzinfo is None:
            logger.warning("Calculating urgency with naive deadline. Assuming UTC.")
            deadline_aware = self.deadline.replace(tzinfo=timezone.utc)
        else:
            deadline_aware = self.deadline

        if now.tzinfo is None:
            logger.warning("Calculating urgency with naive current_datetime. Assuming UTC.")
            now = now.replace(tzinfo=timezone.utc)

        if deadline_aware <= now:
            return 1.0

        created_at_aware = self.created_at
        total_lead_time = deadline_aware - created_at_aware

        if total_lead_time.total_seconds() <= 0:
            return 1.0

        time_since_creation = now - created_at_aware
        time_elapsed_ratio = max(0.0, time_since_creation.total_seconds() / total_lead_time.total_seconds())
        urgency = math.pow(time_elapsed_ratio, 2)
        return min(1.0, max(0.0, urgency))


# --- Task Prioritizer Class ---

class TaskPrioritizer:
    """
    Analyzes and prioritizes tasks based on configurable weights and context.

    Calculates a priority score for each task considering its explicit priority,
    deadline urgency, dependencies, and postponement history. Can also provide
    recommendations based on energy patterns.
    """

    DEFAULT_WEIGHTS: Dict[str, float] = {
        "priority": 0.50,
        "deadline": 0.35,
        "dependencies": 0.10,
        "postponed": 0.05,
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        user_energy_pattern: Optional[Dict[int, float]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._weights = self.DEFAULT_WEIGHTS.copy()
        if weights:
            self._weights.update(weights)

        if user_energy_pattern:
            self._user_energy_pattern = user_energy_pattern
        else:
            logger.warning("No user_energy_pattern provided to TaskPrioritizer. Using a default flat pattern (0.5).")
            self._user_energy_pattern = {h: 0.5 for h in range(24)}

        self._config = config or {}
        self._dependency_max_scale: int = self._config.get("dependency_max_scale", 5)
        self._postponed_max_scale: int = self._config.get("postponed_max_scale", 5)

        logger.info(f"TaskPrioritizer initialized. Weights: {self._weights}")
        logger.debug(f"Using energy pattern starting with hour 0: {self._user_energy_pattern.get(0):.2f}")

    def prioritize(
        self,
        tasks: List[Task],
        current_datetime: Optional[datetime] = None,
    ) -> List[Task]:
        if not tasks:
            return []

        now = current_datetime or datetime.now(timezone.utc)
        if now.tzinfo is None:
            logger.warning("Prioritizing with naive current_datetime. Assuming UTC.")
            now = now.replace(tzinfo=timezone.utc)

        dependency_map = self._build_dependency_map(tasks)
        task_scores: List[Tuple[float, str, Task]] = []
        for task in tasks:
            if task.completed:
                continue
            try:
                score = self._calculate_priority_score(task, now, dependency_map)
                task_scores.append((-score, str(task.id), task))
            except Exception as e:
                logger.error(f"Error calculating priority for task '{task.title}' ({task.id}): {e}", exc_info=True)
                task_scores.append((float('inf'), str(task.id), task))

        import heapq
        heapq.heapify(task_scores)
        prioritized_tasks = [heapq.heappop(task_scores)[2] for _ in range(len(task_scores))]

        logger.info(f"Prioritized {len(prioritized_tasks)} tasks.")
        return prioritized_tasks

    def get_energy_pattern(self, profile: Optional[Any] = None) -> Dict[int, float]:
        """
        Returns the energy pattern, potentially adapted based on a user profile.

        Args:
            profile: Optional user profile (e.g., ChronotypeProfile) to adapt pattern.

        Returns:
            Dict[int, float]: The energy pattern (hour 0-23 -> energy 0.0-1.0).
        """
        adapted_pattern = self._user_energy_pattern.copy()
        if profile and hasattr(profile, 'primary_chronotype'):
            from src.core.chronotype import Chronotype
            logger.debug(f"Adapting energy pattern for profile: {profile.primary_chronotype}")
            if profile.primary_chronotype == Chronotype.EARLY_BIRD:
                for h in range(6, 11):
                    adapted_pattern[h] = min(1.0, adapted_pattern.get(h, 0.5) + 0.1)
            elif profile.primary_chronotype == Chronotype.NIGHT_OWL:
                for h in range(17, 22):
                    adapted_pattern[h] = min(1.0, adapted_pattern.get(h, 0.5) + 0.1)
        else:
            logger.debug("No profile provided or profile lacks chronotype, returning base energy pattern.")

        return adapted_pattern

    def _calculate_priority_score(
        self,
        task: Task,
        current_datetime: datetime,
        dependency_map: Dict[UUID, Set[UUID]],
    ) -> float:
        max_prio_val = max(p.value for p in TaskPriority)
        priority_factor = task.priority.value / max_prio_val
        deadline_factor = task.time_urgency_factor(current_datetime)
        dependent_count = len(dependency_map.get(task.id, set()))
        dependencies_factor = min(1.0, dependent_count / max(1, self._dependency_max_scale))
        postponed_factor = min(1.0, task.postponed_count / max(1, self._postponed_max_scale))

        score = (
            self._weights.get("priority", 0.0) * priority_factor +
            self._weights.get("deadline", 0.0) * deadline_factor +
            self._weights.get("dependencies", 0.0) * dependencies_factor +
            self._weights.get("postponed", 0.0) * postponed_factor
        )
        score = max(0.0, score)

        logger.debug(
            f"Task '{task.title}' ({task.id}) Score: {score:.3f} "
            f"(PrioF: {priority_factor:.2f}, DeadlineF: {deadline_factor:.2f}, "
            f"DepF: {dependencies_factor:.2f}, PostponedF: {postponed_factor:.2f})"
        )
        return score

    def _build_dependency_map(self, tasks: List[Task]) -> Dict[UUID, Set[UUID]]:
        prereq_to_dependents: Dict[UUID, Set[UUID]] = {task.id: set() for task in tasks}
        task_ids = {task.id for task in tasks}

        for task in tasks:
            for prereq_id in task.dependencies:
                if prereq_id in prereq_to_dependents:
                    prereq_to_dependents[prereq_id].add(task.id)
                else:
                    logger.warning(f"Task '{task.title}' ({task.id}) lists dependency '{prereq_id}' which is not in the current task list.")
        return prereq_to_dependents

    def recommend_task_order(
        self,
        tasks: List[Task],
        start_datetime: datetime,
        end_datetime: datetime,
    ) -> List[Tuple[Task, datetime]]:
        logger.warning("recommend_task_order provides a heuristic order, prefer ConstraintSchedulerSolver for detailed scheduling.")
        if not tasks:
            return []
        if start_datetime.tzinfo is None or end_datetime.tzinfo is None:
            logger.warning("recommend_task_order received naive datetimes. Assuming UTC.")
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)
            end_datetime = end_datetime.replace(tzinfo=timezone.utc)

        prioritized_tasks = self.prioritize(tasks, start_datetime)
        schedule: List[Tuple[Task, datetime]] = []
        current_time = start_datetime

        for task in prioritized_tasks:
            task_earliest_start = task.earliest_start or start_datetime
            if task_earliest_start.tzinfo is None:
                task_earliest_start = task_earliest_start.replace(tzinfo=timezone.utc)

            placement_time = max(current_time, task_earliest_start)

            if placement_time + task.duration <= end_datetime:
                schedule.append((task, placement_time))
                current_time = placement_time + task.duration
            else:
                logger.debug(f"Task '{task.title}' cannot fit in remaining window.")

            if current_time >= end_datetime:
                break

        return schedule

    def _find_best_energy_match_heuristic(
        self,
        task: Task,
        earliest_start: datetime,
        latest_end: datetime,
        step: timedelta = timedelta(minutes=15),
        lookahead: timedelta = timedelta(hours=1)
    ) -> datetime:
        best_time = earliest_start
        best_match_score = -1.0
        task_energy_norm = task.energy_level.value / max(e.value for e in EnergyLevel)
        current_check_time = earliest_start
        search_end_time = min(earliest_start + lookahead, latest_end - task.duration)

        while current_check_time <= search_end_time:
            hour = current_check_time.hour
            user_energy = self._user_energy_pattern.get(hour, 0.5)
            match_score = 1.0 - abs(user_energy - task_energy_norm)

            if match_score > best_match_score:
                best_match_score = match_score
                best_time = current_check_time

            current_check_time += step
            if current_check_time + task.duration > latest_end:
                break

        return best_time


# --- Module-level Example Usage ---

async def run_example():
    """Runs examples demonstrating TaskPrioritizer functionality."""
    import asyncio
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Running TaskPrioritizer Example ---")
    now = datetime.now(timezone.utc)
    task1 = Task(
        title="Submit Report",
        priority=TaskPriority.HIGH,
        energy_level=EnergyLevel.HIGH,
        duration=timedelta(hours=1),
        deadline=now + timedelta(hours=6)
    )
    task2 = Task(
        title="Team Meeting Prep",
        priority=TaskPriority.MEDIUM,
        energy_level=EnergyLevel.MEDIUM,
        duration=timedelta(minutes=30),
        dependencies={task1.id}
    )
    task3 = Task(
        title="Review Emails",
        priority=TaskPriority.LOW,
        energy_level=EnergyLevel.LOW,
        duration=timedelta(minutes=45)
    )
    task4 = Task(
        title="Plan Weekend",
        priority=TaskPriority.OPTIONAL,
        energy_level=EnergyLevel.LOW,
        duration=timedelta(minutes=20)
    )
    task5 = Task(
        title="Urgent Call",
        priority=TaskPriority.CRITICAL,
        energy_level=EnergyLevel.MEDIUM,
        duration=timedelta(minutes=15),
        deadline=now + timedelta(hours=1)
    )
    tasks = [task1, task2, task3, task4, task5]

    prioritizer = TaskPrioritizer()

    print("\n--- Prioritized Tasks ---")
    prioritized = prioritizer.prioritize(tasks)
    for i, task in enumerate(prioritized):
        urgency = task.time_urgency_factor(now)
        score = prioritizer._calculate_priority_score(task, now, prioritizer._build_dependency_map(tasks))
        print(f"{i+1}. {task.title:<25} (Prio: {task.priority.name:<8} | Score: {score:.3f} | Urgency: {urgency:.2f})")

    print("\n--- Recommended Order (Heuristic) ---")
    start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end_time = now.replace(hour=17, minute=0, second=0, microsecond=0)
    recommended_order = prioritizer.recommend_task_order(tasks, start_time, end_time)
    print(f"Window: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}")
    for task, rec_start in recommended_order:
        rec_end = rec_start + task.duration
        print(f"{rec_start.strftime('%H:%M')} - {rec_end.strftime('%H:%M')}: {task.title}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_example())
