import { Injectable } from '@nestjs/common';

import {
  eq,
  and,
  asc,
  desc,
  gte,
  lte,
  inArray,
  SQL,
  getTableColumns,
} from 'drizzle-orm';

import { DatabaseError as PostgresError } from 'pg';

import { DatabaseException } from '@app/common/exceptions';
import { DateTimeFilter } from '@app/common/types';

import { tasksTable } from '@app/modules/database/schemas';
import { DatabaseService } from '@app/modules/database/database.service';

import {
  CreateTaskDto,
  Task,
  TasksFindOptions,
  UpdateTaskDto,
  TaskStatus,
} from './types';
import {
  TaskCannotBeDeletedException,
  TaskNotFoundException,
} from './exceptions';

const getDefaultStartDateString = (): string => {
  const defaultStartDate = new Date();

  defaultStartDate.setHours(0);
  defaultStartDate.setMinutes(0);
  defaultStartDate.setSeconds(0);
  defaultStartDate.setMilliseconds(0);

  return defaultStartDate.toISOString();
};

const getDefaultEndDateString = (): string => {
  const defaultEndDate = new Date();

  defaultEndDate.setHours(23);
  defaultEndDate.setMinutes(59);
  defaultEndDate.setSeconds(59);
  defaultEndDate.setMilliseconds(999);
  defaultEndDate.setDate(defaultEndDate.getDate() + 7);

  return defaultEndDate.toISOString();
};

const getStatusFilter = (status?: TaskStatus | TaskStatus[]) => {
  let filter: SQL | undefined = undefined;

  if (status) {
    if (Array.isArray(status)) {
      filter = inArray(tasksTable.status, status);
    } else {
      filter = eq(tasksTable.status, status);
    }
  }

  return filter;
};

const getTimestampFilter = (
  column: 'createdAt' | 'updatedAt' | 'dueTo',
  value?: DateTimeFilter,
) => {
  const defaultStartDate = new Date(getDefaultStartDateString());
  const defaultEndDate = new Date(getDefaultEndDateString());

  let filter: SQL | undefined = undefined;

  if (value) {
    if (typeof value === 'string') {
      filter = eq(tasksTable[column], new Date(value));
    } else {
      filter = and(
        gte(
          tasksTable[column],
          value.start ? new Date(value.start) : defaultStartDate,
        ),
        lte(
          tasksTable[column],
          value.end ? new Date(value.end) : defaultEndDate,
        ),
      );
    }
  }

  return filter;
};

/**
 * Repository for managing tasks.
 */
@Injectable({})
export class TasksRepository {
  constructor(private readonly database: DatabaseService) {}

  /**
   * Creates a new task.
   * @param {CreateTaskDto} newTask - The new task data.
   * @returns {Promise<Task>} A promise that resolves to the created task.
   * @throws {DatabaseException} If there is an error creating the task.
   */
  async create(newTask: CreateTaskDto): Promise<Task> {
    try {
      const [createdTask] = await this.database.db
        .insert(tasksTable)
        .values({
          ...newTask,
          dueTo: newTask.dueTo ? new Date(newTask.dueTo) : null,
        })
        .returning();

      const task: Task = {
        ...createdTask,
        createdAt: createdTask.createdAt.toISOString(),
        updatedAt: createdTask.updatedAt.toISOString(),
        dueTo: createdTask.dueTo ? createdTask.dueTo.toISOString() : null,
      };

      return task;
    } catch (err) {
      throw new DatabaseException('Failed to create task', err, true);
    }
  }

  async findMany(options: TasksFindOptions): Promise<Task[]> {
    const {
      limit = 10,
      page = 0,
      orderBy = 'createdAt',
      sortBy = 'desc',
      where,
    } = options;

    const name = where?.name;
    const id = where?.id;
    const userId = where?.userId;
    const status = where?.status;
    const dueTo = where?.dueTo;
    const repeat = where?.repeat;
    const createdAt = where?.createdAt;
    const updatedAt = where?.updatedAt;

    const dueToFilter = getTimestampFilter('dueTo', dueTo);
    const createdAtFilter = getTimestampFilter('createdAt', createdAt);
    const updatedAtFilter = getTimestampFilter('updatedAt', updatedAt);
    const statusFilter = getStatusFilter(status);

    try {
      const tasks = await this.database.db
        .select()
        .from(tasksTable)
        .where(
          and(
            name ? eq(tasksTable.name, name) : undefined,
            id ? eq(tasksTable.id, id) : undefined,
            userId ? eq(tasksTable.userId, userId) : undefined,
            statusFilter,
            dueToFilter,
            repeat ? eq(tasksTable.repeat, repeat) : undefined,
            createdAtFilter,
            updatedAtFilter,
          ),
        )
        .limit(limit)
        .offset(page * limit)
        .orderBy(
          sortBy === 'asc'
            ? asc(tasksTable[orderBy])
            : desc(tasksTable[orderBy]),
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
      throw new DatabaseException('Failed to find tasks', err, true);
    }
  }

  /**
   * Finds a task by ID and user ID.
   * @param {string} id - The ID of the task.
   * @param {string} userId - The ID of the user.
   * @returns {Promise<Task>} A promise that resolves to the task.
   * @throws {TaskNotFoundException} If the task is not found.
   * @throws {DatabaseException} If there is an error finding the task.
   */
  async findOne(id: string, userId: string): Promise<Task> {
    try {
      const result = await this.database.db
        .select()
        .from(tasksTable)
        .where(and(eq(tasksTable.id, id), eq(tasksTable.userId, userId)))
        .limit(1);

      if (result.length <= 0) {
        throw new TaskNotFoundException(id);
      }

      return {
        ...result[0],
        createdAt: result[0].createdAt.toISOString(),
        updatedAt: result[0].updatedAt.toISOString(),
        dueTo: result[0].dueTo ? result[0].dueTo.toISOString() : null,
      };
    } catch (err) {
      if (err instanceof PostgresError) {
        throw new DatabaseException('Failed to find task', err, true);
      }

      throw err;
    }
  }
  /**
   * Finds a task by ID.
   * @param {string} id - The ID of the task.
   * @returns {Promise<Task>} A promise that resolves to the task.
   * @throws {TaskNotFoundException} If the task is not found.
   * @throws {DatabaseException} If there is an error finding the task.
   */
  async findById(id: string): Promise<Task> {
    try {
      const result = await this.database.db
        .select()
        .from(tasksTable)
        .where(eq(tasksTable.id, id))
        .limit(1);

      if (result.length <= 0) {
        throw new TaskNotFoundException(id);
      }

      return {
        ...result[0],
        createdAt: result[0].createdAt.toISOString(),
        updatedAt: result[0].updatedAt.toISOString(),
        dueTo: result[0].dueTo ? result[0].dueTo.toISOString() : null,
      };
    } catch (err) {
      if (err instanceof PostgresError) {
        throw new DatabaseException('Failed to find task by id', err, true);
      }

      throw err;
    }
  }

  /**
   * Updates a task by ID and user ID.
   * @param {string} id - The ID of the task.
   * @param {string} userId - The ID of the user.
   * @param {UpdateTaskDto} newTask - The new task data.
   * @returns {Promise<Task>} A promise that resolves to the updated task.
   * @throws {DatabaseException} If there is an error updating the task.
   */
  async updateOne(
    id: string,
    userId: string,
    newTask: UpdateTaskDto,
  ): Promise<Task> {
    try {
      const result = await this.database.db
        .update(tasksTable)
        .set({
          ...newTask,
          createdAt: undefined,
          updatedAt: new Date(),
          dueTo: newTask.dueTo
            ? new Date(newTask.dueTo)
            : newTask.dueTo === null
              ? null
              : undefined,
          repeat: newTask.repeat
            ? newTask.repeat
            : newTask.repeat === null
              ? null
              : undefined,
        })
        .where(
          and(
            eq(tasksTable.id, id),
            userId ? eq(tasksTable.userId, userId) : undefined,
          ),
        )
        .returning();

      if (result.length <= 0) {
        throw new TaskNotFoundException(id);
      }

      return {
        ...result[0],
        createdAt: result[0].createdAt.toISOString(),
        updatedAt: result[0].updatedAt.toISOString(),
        dueTo: result[0].dueTo ? result[0].dueTo.toISOString() : null,
      };
    } catch (err) {
      if (err instanceof PostgresError) {
        throw new DatabaseException('Failed to update one task', err, true);
      }

      throw err;
    }
  }

  /**
   * Removes a task by ID and user ID.
   * @param {string} id - The ID of the task.
   * @param {string} userId - The ID of the user.
   * @returns {Promise<void>} A promise that resolves when the task is removed.
   * @throws {TaskNotFoundException} If the task is not found.
   * @throws {DatabaseException} If there is an error removing the task.
   */
  async removeOne(id: string, userId: string): Promise<void> {
    try {
      const result = await this.database.db
        .delete(tasksTable)
        .where(
          and(
            eq(tasksTable.id, id),
            userId ? eq(tasksTable.userId, userId) : undefined,
          ),
        );

      if (!result.rowCount) {
        throw new TaskNotFoundException(id);
      }
    } catch (err) {
      if (err instanceof PostgresError) {
        // foreign_key_violation
        if (err.code === '23503') {
          throw new TaskCannotBeDeletedException(id);
        }

        throw new DatabaseException('Failed to remove one task', err, true);
      }

      throw err;
    }
  }
}
