# === File: scheduler-core/tests/unit/test_scheduler.py ===

"""
Unit Tests for the Scheduler Orchestration Module.

Tests the functionality of the `Scheduler` class in isolation, mocking its
dependencies (SleepCalculator, ChronotypeAnalyzer, TaskPrioritizer,
ConstraintSchedulerSolver, LLMEngine) to verify its orchestration logic,
data preparation, and output formatting.
"""

import logging
from datetime import date, time, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# Modules to test
try:
    from src.core.scheduler import Scheduler, ScheduleInputData, GeneratedSchedule
    from src.core.task_prioritizer import Task, TaskPriority, EnergyLevel
    from src.core.chronotype import Chronotype, ChronotypeProfile
    from src.core.sleep import SleepMetrics
    from src.core.constraint_solver import ScheduledTaskInfo, SolverInput
    # Import other necessary types
    SCHEDULER_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).error(f"Failed to import modules for test_scheduler: {e}")
    SCHEDULER_AVAILABLE = False
    # Define dummy classes if imports fail, needed for test structure
    class Scheduler: pass
    class ScheduleInputData: pass
    class GeneratedSchedule: pass
    class Task: pass
    class TaskPriority: pass
    class EnergyLevel: pass
    class Chronotype: pass
    class ChronotypeProfile: pass
    class SleepMetrics: pass
    class ScheduledTaskInfo: pass
    class SolverInput: pass


# Skip all tests in this file if the core scheduler module isn't available
pytestmark = pytest.mark.skipif(not SCHEDULER_AVAILABLE, reason="Scheduler module or its dependencies not found.")


# --- Fixtures ---

@pytest.fixture
def mock_dependencies():
    """Provides mock instances for all Scheduler dependencies."""
    mock_sleep_calc = MagicMock(name="MockSleepCalculator")
    mock_chrono_analyzer = MagicMock(name="MockChronotypeAnalyzer")
    mock_task_prio = MagicMock(name="MockTaskPrioritizer")
    # Mock the solve method of the constraint solver
    mock_solver = MagicMock(name="MockConstraintSolver")
    # Mock LLM engine (optional dependency)
    mock_llm = MagicMock(name="MockLLMEngine") # or None if not testing LLM integration

    # Configure default return values for mock methods if needed
    mock_chrono_analyzer.determine_chronotype_from_meq.return_value = Chronotype.INTERMEDIATE
    mock_chrono_analyzer.create_chronotype_profile.return_value = ChronotypeProfile(user_id=uuid4(), primary_chronotype=Chronotype.INTERMEDIATE)
    mock_sleep_calc.calculate_sleep_window.return_value = SleepMetrics(
        ideal_duration=timedelta(hours=8), ideal_bedtime=time(23,0), ideal_wake_time=time(7,0)
    )
    # Default solver result: return a list containing info for one task
    mock_solver.solve.return_value = [
        ScheduledTaskInfo(task_id=uuid4(), start_time=time(9,0), end_time=time(10,0), task_date=date.today())
    ]
    # Mock the energy pattern method if TaskPrioritizer has it
    mock_task_prio.get_energy_pattern.return_value = {h: 0.5 for h in range(24)} # Default flat energy

    return {
        "sleep_calculator": mock_sleep_calc,
        "chronotype_analyzer": mock_chrono_analyzer,
        "task_prioritizer": mock_task_prio,
        "constraint_solver": mock_solver,
        "llm_engine": mock_llm,
    }


@pytest.fixture
def scheduler_instance(mock_dependencies):
    """Provides an instance of the Scheduler with mocked dependencies."""
    return Scheduler(**mock_dependencies)


@pytest.fixture
def sample_input_data():
    """Provides a sample ScheduleInputData object for tests."""
    user_id = uuid4()
    target_date = date.today() + timedelta(days=1)
    # Use Task class if available, otherwise dict
    TaskCls = Task if 'Task' in globals() and isinstance(Task, type) else dict
    task1 = TaskCls(id=uuid4(), title="Task 1", priority=TaskPriority.HIGH, energy_level=EnergyLevel.HIGH, duration=timedelta(hours=1))
    task2 = TaskCls(id=uuid4(), title="Task 2", priority=TaskPriority.MEDIUM, energy_level=EnergyLevel.LOW, duration=timedelta(minutes=30))

    return ScheduleInputData(
        user_id=user_id,
        target_date=target_date,
        tasks=[task1, task2], # type: ignore
        fixed_events_input=[{"id": "lunch", "start_time": "12:00", "end_time": "13:00"}],
        preferences={"work_start_time": "09:00", "work_end_time": "17:00"},
        user_profile={"age": 30, "meq_score": 50},
    )


# --- Test Cases ---

@pytest.mark.asyncio
async def test_generate_schedule_successful_run(scheduler_instance, sample_input_data, mock_dependencies):
    """
    Test the happy path of generate_schedule: valid input, solver finds solution.
    """
    # Configure solver mock to return a specific result for this test
    task1_id = sample_input_data.tasks[0].id
    task2_id = sample_input_data.tasks[1].id
    mock_solver_result = [
        ScheduledTaskInfo(task_id=task1_id, start_time=time(9, 30), end_time=time(10, 30), task_date=sample_input_data.target_date),
        ScheduledTaskInfo(task_id=task2_id, start_time=time(11, 0), end_time=time(11, 30), task_date=sample_input_data.target_date),
    ]
    mock_dependencies["constraint_solver"].solve.return_value = mock_solver_result

    # Call the method under test
    result = await scheduler_instance.generate_schedule(sample_input_data)

    # Assertions
    assert isinstance(result, GeneratedSchedule)
    assert result.user_id == sample_input_data.user_id
    assert result.target_date == sample_input_data.target_date
    assert not result.warnings # Expect no warnings on happy path
    assert len(result.scheduled_items) == 3 # 2 tasks + 1 fixed event

    # Check if dependencies were called correctly
    mock_dependencies["chronotype_analyzer"].determine_chronotype_from_meq.assert_called_once_with(50)
    mock_dependencies["sleep_calculator"].calculate_sleep_window.assert_called_once()
    mock_dependencies["constraint_solver"].solve.assert_called_once()

    # Check solver input preparation (example)
    solver_call_args = mock_dependencies["constraint_solver"].solve.call_args[0]
    solver_input_arg: SolverInput = solver_call_args[0]
    assert isinstance(solver_input_arg, SolverInput)
    assert len(solver_input_arg.tasks) == 2
    assert solver_input_arg.tasks[0].id == task1_id
    assert solver_input_arg.tasks[0].duration_minutes == 60
    assert len(solver_input_arg.fixed_events) == 1
    assert solver_input_arg.fixed_events[0].id == "lunch"

    # Check output formatting (example)
    assert result.scheduled_items[0]["type"] == "task"
    assert result.scheduled_items[0]["task_id"] == str(task1_id)
    assert result.scheduled_items[0]["start_time"] == "09:30"
    assert result.scheduled_items[1]["type"] == "task"
    assert result.scheduled_items[1]["task_id"] == str(task2_id)
    assert result.scheduled_items[2]["type"] == "fixed_event" # Assuming fixed events are added last after sorting
    assert result.scheduled_items[2]["event_id"] == "lunch"


@pytest.mark.asyncio
async def test_generate_schedule_solver_no_solution(scheduler_instance, sample_input_data, mock_dependencies):
    """
    Test the case where the constraint solver fails to find a solution.
    """
    # Configure solver mock to return None
    mock_dependencies["constraint_solver"].solve.return_value = None

    result = await scheduler_instance.generate_schedule(sample_input_data)

    assert isinstance(result, GeneratedSchedule)
    assert result.user_id == sample_input_data.user_id
    assert result.target_date == sample_input_data.target_date
    assert len(result.scheduled_items) == 0 # Expect empty schedule on solver failure (current logic)
    assert len(result.warnings) > 0
    assert "Could not find a feasible schedule" in result.warnings[0]
    assert result.metrics.get("status") == "failed" # Check if metrics indicate failure

    mock_dependencies["constraint_solver"].solve.assert_called_once()


@pytest.mark.asyncio
async def test_generate_schedule_no_tasks(scheduler_instance, sample_input_data, mock_dependencies):
    """
    Test generating a schedule when the input contains no tasks.
    """
    sample_input_data.tasks = [] # Remove tasks

    result = await scheduler_instance.generate_schedule(sample_input_data)

    assert isinstance(result, GeneratedSchedule)
    assert result.user_id == sample_input_data.user_id
    assert result.target_date == sample_input_data.target_date
    assert len(result.scheduled_items) == 0 # Expect empty schedule
    assert len(result.warnings) > 0
    assert "No tasks to schedule" in result.warnings[0]
    assert result.metrics.get("status") != "failed" # Should not be a failure, just nothing to schedule

    # Solver should not be called if there are no tasks after preparation
    mock_dependencies["constraint_solver"].solve.assert_not_called()


@pytest.mark.asyncio
async def test_generate_schedule_invalid_fixed_event(scheduler_instance, sample_input_data, mock_dependencies):
    """
    Test that invalid fixed event data is handled gracefully.
    """
    # Add an invalid event
    sample_input_data.fixed_events_input.append({"id": "invalid", "start_time": "14:00", "end_time": "13:00"}) # End before start

    # Configure solver to return a valid result for the tasks
    task1_id = sample_input_data.tasks[0].id
    mock_solver_result = [
        ScheduledTaskInfo(task_id=task1_id, start_time=time(9, 0), end_time=time(10, 0), task_date=sample_input_data.target_date)
    ]
    mock_dependencies["constraint_solver"].solve.return_value = mock_solver_result

    result = await scheduler_instance.generate_schedule(sample_input_data)

    assert isinstance(result, GeneratedSchedule)
    # Solver should still run with valid tasks and the *valid* fixed event
    mock_dependencies["constraint_solver"].solve.assert_called_once()
    solver_call_args = mock_dependencies["constraint_solver"].solve.call_args[0]
    solver_input_arg: SolverInput = solver_call_args[0]
    assert len(solver_input_arg.fixed_events) == 1 # Only the valid lunch event should be passed
    assert solver_input_arg.fixed_events[0].id == "lunch"

    # Check that the final schedule contains the task and the valid fixed event
    assert len(result.scheduled_items) == 2
    assert any(item['type'] == 'task' and item['task_id'] == str(task1_id) for item in result.scheduled_items)
    assert any(item['type'] == 'fixed_event' and item['event_id'] == 'lunch' for item in result.scheduled_items)


# TODO: Add more tests:
# - Test with different chronotypes affecting results (requires mocking profile creation/loading).
# - Test with different preferences affecting the scheduling window.
# - Test task dependency handling in solver input preparation.
# - Test deadline/earliest_start constraint preparation.
# - Test error handling within _prepare_user_context and _prepare_solver_input.
# - Test LLM integration if enabled (mocking the LLM call).
# - Test break insertion logic when implemented.
# - Test metric calculation logic when implemented.
