import { Injectable } from '@nestjs/common';

import { and, eq, asc, desc } from 'drizzle-orm';

import { DatabaseError as PostgresError } from 'pg';

import { DatabaseException } from '@app/common/exceptions';

import { schedulesTable } from '@app/modules/database/schemas';
import { DatabaseService } from '@app/modules/database/database.service';

import {
  Schedule,
  CreateScheduleDto,
  UpdateScheduleDto,
  SchedulesFindManyOptions,
} from './types';

import { ScheduleCannotBeDeletedException, ScheduleNotFoundException } from './exceptions';
/**
 * Repository for managing schedules.
 */
@Injectable()
export class SchedulesRepository {
  constructor(private readonly database: DatabaseService) { }

  /**
   * Finds multiple schedules based on the provided options.
   * @param {SchedulesFindManyOptions} options - The options to filter schedules.
   * @returns {Promise<Schedule[]>} A promise that resolves to an array of schedules.
   * @throws {DatabaseException} If there is an error finding schedules.
   */
  async findMany(options: SchedulesFindManyOptions): Promise<Schedule[]> {
    const { limit = 10, orderBy = 'createdAt', page = 0, sortBy = 'desc', where } = options

    const userId = where?.userId

    try {
      const result = await this.database.db
        .select()
        .from(schedulesTable)
        .where(
          and(
            userId ? eq(schedulesTable.userId, userId) : undefined
          )
        )
        .limit(limit)
        .offset(page * limit)
        .orderBy(
          sortBy === 'asc'
            ? asc(schedulesTable[orderBy])
            : desc(schedulesTable[orderBy]),
        )

      return result.map((schedule) => {
        return {
          ...schedule,
          createdAt: schedule.createdAt.toISOString(),
          updatedAt: schedule.updatedAt.toISOString(),
        };
      });
    } catch (err) {
      throw new DatabaseException('Failed to find many schedules', err, true);
    }
  }

  /**
   * Finds a schedule by ID and user ID.
   * @param {string} id - The ID of the schedule.
   * @param {string} userId - The ID of the user.
   * @returns {Promise<Schedule>} A promise that resolves to the schedule.
   * @throws {ScheduleNotFoundException} If the schedule is not found.
   * @throws {DatabaseException} If there is an error finding the schedule.
   */
  async findOne(id: string, userId: string): Promise<Schedule> {
    try {
      const result = (
        await this.database.db
          .select()
          .from(schedulesTable)
          .where(
            and(eq(schedulesTable.id, id), eq(schedulesTable.userId, userId)),
          )
          .limit(1)
      ).map((schedule) => {
        return {
          ...schedule,
          createdAt: schedule.createdAt.toISOString(),
          updatedAt: schedule.updatedAt.toISOString(),
        };
      });

      if (result.length <= 0) {
        throw new ScheduleNotFoundException(id);
      }

      return result[0];
    } catch (err) {
      if (err instanceof PostgresError) {
        throw new DatabaseException('Failed to find one schedule', err, true);
      }

      throw err;
    }
  }

  /**
   * Creates a new schedule.
   * @param {CreateScheduleDto} createDto - The new schedule data.
   * @returns {Promise<Schedule>} A promise that resolves to the created schedule.
   * @throws {DatabaseException} If there is an error creating the schedule.
   */
  async create(createDto: CreateScheduleDto): Promise<Schedule> {
    try {
      const result = (
        await this.database.db
          .insert(schedulesTable)
          .values(createDto)
          .returning()
      ).map((schedule) => {
        return {
          ...schedule,
          createdAt: schedule.createdAt.toISOString(),
          updatedAt: schedule.updatedAt.toISOString(),
        };
      });

      return result[0];
    } catch (err) {
      throw new DatabaseException('Failed to create schedule', err, true);
    }
  }

  /**
   * Updates a schedule by ID and user ID.
   * @param {string} id - The ID of the schedule.
   * @param {string} userId - The ID of the user.
   * @param {UpdateScheduleDto} newSchedule - The new schedule data.
   * @returns {Promise<Schedule>} A promise that resolves to the updated schedule.
   * @throws {ScheduleNotFoundException} If the schedule is not found.
   * @throws {DatabaseException} If there is an error updating the schedule.
   */
  async updateOne(
    id: string,
    userId: string,
    updateDto: UpdateScheduleDto,
  ): Promise<void> {
    try {
      const result = await this.database.db
        .update(schedulesTable)
        .set({
          name: updateDto.name || undefined,
          description: updateDto.description,
        })
        .where(
          and(eq(schedulesTable.id, id), eq(schedulesTable.userId, userId)),
        );

      if (!result.rowCount) {
        throw new ScheduleNotFoundException(id);
      }
    } catch (err) {
      if (err instanceof PostgresError) {
        throw new DatabaseException('Failed to update one schedule', err, true);
      }

      throw err;
    }
  }

  /**
   * Removes a schedule by ID and user ID.
   * @param {string} id - The ID of the schedule.
   * @param {string} userId - The ID of the user.
   * @returns {Promise<void>} A promise that resolves when the schedule is removed.
   * @throws {ScheduleNotFoundException} If the schedule is not found.
   * @throws {DatabaseException} If there is an error removing the schedule.
   */
  async removeOne(id: string, userId: string): Promise<void> {
    try {
      const result = await this.database.db
        .delete(schedulesTable)
        .where(
          and(eq(schedulesTable.id, id), eq(schedulesTable.userId, userId)),
        );

      if (!result.rowCount) {
        throw new ScheduleNotFoundException(id);
      }
    } catch (err) {
      if (err instanceof PostgresError) {

        if (err.code === '23503') {
          throw new ScheduleCannotBeDeletedException(id)
        }

        throw new DatabaseException('Failed to remove one schedule', err, true);
      }

      throw err;
    }
  }
}
