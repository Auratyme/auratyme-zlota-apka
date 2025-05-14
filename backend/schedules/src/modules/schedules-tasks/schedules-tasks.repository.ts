import { Injectable } from '@nestjs/common';

import { DatabaseError as PostgresError } from 'pg';

import { getTableColumns, eq, and } from 'drizzle-orm';

import {
  schedulesTasksTable,
  tasksTable,
  schedulesTable,
} from '../database/schemas';

import { Task } from '../tasks/types';

import { DatabaseService } from '../database/database.service';
import { DatabaseException } from '@app/common/exceptions';

import { SchedulesRepository } from '../schedules/schedules.repository';
import { TasksRepository } from '../tasks/tasks.repository';
import { Schedule } from '../schedules/types';

/**
 * Repository for managing the relationship between schedules and tasks.
 */
@Injectable()
export class SchedulesTasksRepository {
  constructor(
    private readonly schedulesRepository: SchedulesRepository,
    private readonly tasksRepository: TasksRepository,
    private readonly database: DatabaseService,
  ) { }

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

      await this.database.db.insert(schedulesTasksTable).values({
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
          schedulesTasksTable,
          eq(tasksTable.id, schedulesTasksTable.taskId),
        )
        .where(
          and(
            eq(schedulesTasksTable.scheduleId, scheduleId),
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
   * Finds schedules for a given task.
   * @param {string} taskId - The ID of the task.
   * @param {string} userId - The ID of the user.
   * @returns {Promise<Schedule[]>} A promise that resolves to an array of tasks.
   * @throws {DatabaseException} If there is an error finding tasks.
   * @throws {TaskNotFoundException} If task is not found
   */
  async findSchedulesForTask(
    taskId: string,
    userId: string
  ): Promise<Schedule[]> {
    try {
      await this.tasksRepository.findOne(taskId, userId)

      const schedules = await this.database.db
        .select(getTableColumns(schedulesTable))
        .from(schedulesTable)
        .innerJoin(
          schedulesTasksTable,
          eq(schedulesTable.id, schedulesTasksTable.scheduleId)
        )
        .where(
          and(
            eq(schedulesTable.userId, userId),
            eq(schedulesTasksTable.taskId, taskId)
          )
        )

      return schedules.map((schedule) => {
        return {
          ...schedule,
          updatedAt: schedule.updatedAt.toISOString(),
          createdAt: schedule.createdAt.toISOString(),
        }
      })
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
   * Removes all tasks from a schedule.
   * @param {string} scheduleId - The ID of the schedule.
   * @param {string} userId - The ID of the user.
   * @returns {Promise<void>} A promise that resolves when the task is removed from the schedule.
   * @throws {DatabaseException} If there is an error removing the task from the schedule.
   * @throws {ScheduleNotFoundException} If schedule is not found
   */
  async removeAllTasksFromSchedule(
    scheduleId: string,
    userId: string,
    force: boolean = false): Promise<void> {
    try {
      await this.schedulesRepository.findOne(scheduleId, userId)

      const result = await this.database.db
        .delete(schedulesTasksTable)
        .where(and(
          eq(schedulesTasksTable.scheduleId, scheduleId),
        ))
        .returning()

      if (force) {
        await this.database.db.transaction(async (tx) => {
          for (const { taskId } of result) {
            try {
              await this.tasksRepository.removeOne(taskId, userId)
            } catch (err) {
              tx.rollback()
            }
          }
        })
      }
    } catch (err) {
      if (err instanceof PostgresError) {
        throw new DatabaseException(
          'Failed to remove all tasks from schedule',
          err,
          true,
        );
      }

      throw err;
    }
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
    try {
      await this.tasksRepository.findOne(taskId, userId)

      await this.database.db
        .delete(schedulesTasksTable)
        .where(eq(schedulesTasksTable.taskId, taskId))
    } catch (err) {
      if (err instanceof PostgresError) {
        throw new DatabaseException(
          'Failed to remove all tasks from schedule',
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
        .delete(schedulesTasksTable)
        .where(
          and(
            eq(schedulesTasksTable.taskId, taskId),
            eq(schedulesTasksTable.scheduleId, scheduleId),
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
