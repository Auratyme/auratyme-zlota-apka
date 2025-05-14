import { Injectable } from '@nestjs/common';

import { TasksService } from '../tasks/tasks.service';
import { SchedulesService } from '../schedules/schedules.service';

import { Task } from '../tasks/types';
import { Schedule } from '../schedules/types';

import { SchedulesTasksRepository } from './schedules-tasks.repository';

@Injectable()
export class SchedulesTasksService {
  constructor(
    private readonly tasksService: TasksService,
    private readonly schedulesService: SchedulesService,
    private readonly schedulesTasksRepository: SchedulesTasksRepository,
  ) { }

  /**
   * Finds tasks for a given schedule ID and user ID.
   * @param {string} scheduleId - The ID of the schedule.
   * @param {string} userId - The ID of the user.
   * @returns {Promise<Task[]>} A promise that resolves to an array of tasks.
   * @throws {DatabaseException} If there is an error finding tasks.
   * @throws {ScheduleNotFoundException} If schedule is not found
   */
  async findTasksForSchedule(
    scheduleId: string,
    userId: string,
  ): Promise<Task[]> {
    return this.schedulesTasksRepository.findTasksForSchedule(
      scheduleId,
      userId,
    );
  }

  async findSchedulesForTask(
    taskId: string,
    userId: string
  ): Promise<Schedule[]> {
    return this.schedulesTasksRepository.findSchedulesForTask(
      taskId, userId
    )
  }

  /**
   * Adds a task to a schedule.
   * @param {string} taskId - The ID of the task.
   * @param {string} scheduleId - The ID of the schedule.
   * @param {string} userId - The ID of the user.
   * @returns {Promise<void>} A promise that resolves when the task is added to the schedule.
   * @throws {DatabaseException} If there is an error adding the task to the schedule.
   * @throws {ScheduleNotFoundException} If schedule is not found
   * @throws {TaskNotFoundException} If task is not found
   */
  async addTaskToSchedule(
    taskId: string,
    scheduleId: string,
    userId: string,
  ): Promise<void> {
    return this.schedulesTasksRepository.addTaskToSchedule(
      taskId,
      scheduleId,
      userId,
    );
  }

  /**
   * Removes all tasks from a schedule.
   * @param {string} scheduleId - The ID of the schedule.
   * @param {string} userId - The ID of the user.
   * @returns {Promise<void>} A promise that resolves when the task is removed from the schedule.
   * @throws {DatabaseException} If there is an error removing the task from the schedule.
   * @throws {ScheduleNotFoundException} If schedule is not found
   */
  async removeAllTasksFromSchedule(scheduleId: string, userId: string, force: boolean = false): Promise<void> {
    return this.schedulesTasksRepository.removeAllTasksFromSchedule(
      scheduleId,
      userId,
      force
    )
  }

  /**
   * Removes task from all schedules.
   * @param {string} taskId
   * @param {string} userId
   * @returns {Promise<void>}
   * @throws {DatabaseException}
   * @throws {TaskNotFoundException}
   */
  async removeTaskFromAllSchedules(taskId: string, userId: string): Promise<void> {
    return this.schedulesTasksRepository.removeTaskFromAllSchedules(
      taskId, userId
    )
  }

  /**
   * Removes a task from a schedule.
   * @param {string} taskId - The ID of the task.
   * @param {string} scheduleId - The ID of the schedule.
   * @param {string} userId - The ID of the user.
   * @returns {Promise<void>} A promise that resolves when the task is removed from the schedule.
   * @throws {DatabaseException} If there is an error removing the task from the schedule.
   * @throws {ScheduleNotFoundException} If schedule is not found
   * @throws {TaskNotFoundException} If task is not found
   */
  async removeTaskFromSchedule(
    taskId: string,
    scheduleId: string,
    userId: string,
  ): Promise<void> {
    return this.schedulesTasksRepository.removeTaskFromSchedule(
      taskId,
      scheduleId,
      userId,
    );
  }
}
