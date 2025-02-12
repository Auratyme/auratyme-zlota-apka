import { Injectable } from '@nestjs/common';

import {
  Schedule,
  CreateScheduleDto,
  UpdateScheduleDto,
  SchedulesFindManyOptions,
} from './types';

import { SchedulesRepository } from './schedules.repository';

/**
 * Service for managing schedules.
 */
@Injectable()
export class SchedulesService {
  constructor(private readonly schedulesRepository: SchedulesRepository) {}

  /**
   * Finds multiple schedules based on the provided options.
   * @param {SchedulesFindManyOptions} options - The options to filter schedules.
   * @returns {Promise<Schedule[]>} A promise that resolves to an array of schedules.
   * @throws {DatabaseException} If there is an error finding schedules.
   */
  async findMany(options: SchedulesFindManyOptions): Promise<Schedule[]> {
    const findManyPromise = this.schedulesRepository.findMany(options);

    return findManyPromise;
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
    const findOnePromise = this.schedulesRepository.findOne(id, userId);

    return findOnePromise;
  }

  /**
   * Creates a new schedule.
   * @param {CreateScheduleDto} createDto - The new schedule data.
   * @returns {Promise<Schedule>} A promise that resolves to the created schedule.
   * @throws {DatabaseException} If there is an error creating the schedule.
   */
  async create(createDto: CreateScheduleDto): Promise<Schedule> {
    const createPromise = this.schedulesRepository.create(createDto);

    return createPromise;
  }

  /**
   * Updates a schedule by ID and user ID.
   * @param {string} id - The ID of the schedule.
   * @param {string} userId - The ID of the user.
   * @param {UpdateScheduleDto} updateDto - The new schedule data.
   * @returns {Promise<Schedule>} A promise that resolves to the updated schedule.
   * @throws {ScheduleNotFoundException} If the schedule is not found.
   * @throws {DatabaseException} If there is an error updating the schedule.
   */
  async updateOne(
    id: string,
    userId: string,
    updateDto: UpdateScheduleDto,
  ): Promise<void> {
    const updateOnePromise = this.schedulesRepository.updateOne(
      id,
      userId,
      updateDto,
    );

    return updateOnePromise;
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
    const removeOnePromise = this.schedulesRepository.removeOne(id, userId);

    return removeOnePromise;
  }
}
