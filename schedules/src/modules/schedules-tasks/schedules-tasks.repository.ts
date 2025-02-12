import { Injectable } from '@nestjs/common';

import { DatabaseError as PostgresError } from 'pg';

import { getTableColumns, eq, and } from 'drizzle-orm';

import {
  scheduleTasksTable,
  tasksTable,
  schedulesTable,
} from '../database/schemas';

import { Task } from '../tasks/types';

import { DatabaseService } from '../database/database.service';
import { DatabaseException } from '@app/common/exceptions';

import { SchedulesRepository } from '../schedules/schedules.repository';
import { TasksRepository } from '../tasks/tasks.repository';

/**
 * Repository for managing the relationship between schedules and tasks.
 */
@Injectable()
export class SchedulesTasksRepository {
  constructor(
    private readonly schedulesRepository: SchedulesRepository,
    private readonly tasksRepository: TasksRepository,
    private readonly database: DatabaseService,
  ) {}

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
    try {
      const task = await this.tasksRepository.findOne(taskId, userId);
      const schedule = await this.schedulesRepository.findOne(
        scheduleId,
        userId,
      );

      await this.database.db.insert(scheduleTasksTable).values({
        scheduleId: schedule.id,
        taskId: task.id,
      });
    } catch (err) {
      if (err instanceof PostgresError) {
        throw new DatabaseException(
          'Failed to add task to schedule',
          err,
          true,
        );
      }

      throw err;
    }
  }

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
    try {
      await this.schedulesRepository.findOne(scheduleId, userId);

      const tasks = await this.database.db
        .select(getTableColumns(tasksTable))
        .from(tasksTable)
        .innerJoin(
          scheduleTasksTable,
          eq(tasksTable.id, scheduleTasksTable.taskId),
        )
        .where(
          and(
            eq(scheduleTasksTable.scheduleId, scheduleId),
            eq(tasksTable.userId, userId),
          ),
        );

      return tasks.map((task) => {
        return {
          ...task,
          updatedAt: task.updatedAt.toISOString(),
          createdAt: task.createdAt.toISOString(),
          dueTo: task.dueTo ? task.dueTo.toISOString() : null,
        };
      });
    } catch (err) {
      if (err instanceof PostgresError) {
        throw new DatabaseException(
          'Failed find tasks for schedule',
          err,
          true,
        );
      }

      throw err;
    }
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
    try {
      await this.schedulesRepository.findOne(scheduleId, userId);
      await this.tasksRepository.findOne(taskId, userId);

      await this.database.db
        .delete(scheduleTasksTable)
        .where(
          and(
            eq(scheduleTasksTable.taskId, taskId),
            eq(scheduleTasksTable.scheduleId, scheduleId),
          ),
        );
    } catch (err) {
      if (err instanceof PostgresError) {
        throw new DatabaseException(
          'Failed to remove task from schedule',
          err,
          true,
        );
      }

      throw err;
    }
  }
}
