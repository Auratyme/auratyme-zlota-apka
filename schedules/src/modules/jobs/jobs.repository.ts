import { Injectable } from '@nestjs/common';

import { eq } from 'drizzle-orm';

import { jobsTable } from '@app/modules/database/schemas';

import { DatabaseException } from '@app/common/exceptions';

import { DatabaseService } from '@app/modules/database/database.service';

import {
  CreateJobDto,
  Job,
  UpdateJobDto,
  JobFindOptions,
  JobRemoveOptions,
  JobUpdateOptions,
} from './types';

@Injectable()
export class JobsRepository {
  constructor(private database: DatabaseService) {}
  async create(newJob: CreateJobDto): Promise<Job> {
    try {
      const result = await this.database.db
        .insert(jobsTable)
        .values(newJob)
        .returning();

      return result[0];
    } catch (err) {
      throw new DatabaseException('Failed to create job', err, true);
    }
  }

  async findMany(options: JobFindOptions): Promise<Job[]> {
    try {
      const result = await this.database.db.select().from(jobsTable);

      return result;
    } catch (err) {
      throw new DatabaseException('failed to find many jobs', err, true);
    }
  }
  async findByAttributes(attributes: Record<string, any>): Promise<Job[]> {
    try {
      const result = await this.database.db
        .select()
        .from(jobsTable)
        .where(eq(jobsTable.attributes, attributes));

      return result;
    } catch (err) {
      throw new DatabaseException(
        `failed to find jobs by attributes`,
        err,
        true,
      );
    }
  }
  async findById(id: string): Promise<Job | null> {
    try {
      const result = await this.database.db
        .select()
        .from(jobsTable)
        .where(eq(jobsTable.id, id));

      return result.length <= 0 ? null : result[0];
    } catch (err) {
      throw new DatabaseException('failed to find job by id', err, true);
    }
  }

  async updateMany(
    options: JobUpdateOptions,
    newJob: UpdateJobDto,
  ): Promise<Job[]> {
    try {
      const result = await this.database.db
        .update(jobsTable)
        .set(newJob)
        .returning();

      return result;
    } catch (err) {
      throw new DatabaseException('failed to update many jobs', err, true);
    }
  }
  async updateById(id: string, newJob: UpdateJobDto): Promise<Job | null> {
    try {
      const result = await this.database.db
        .update(jobsTable)
        .set(newJob)
        .where(eq(jobsTable.id, id))
        .returning();

      return result.length <= 0 ? null : result[0];
    } catch (err) {
      throw new DatabaseException('failed to update job by id', err, true);
    }
  }

  async removeMany(options: JobRemoveOptions): Promise<Job[]> {
    try {
      const result = await this.database.db.delete(jobsTable).returning();

      return result;
    } catch (err) {
      throw new DatabaseException('failed to remove many jobs', err, true);
    }
  }
  async removeById(id: string): Promise<Job | null> {
    try {
      const result = await this.database.db
        .delete(jobsTable)
        .where(eq(jobsTable.id, id))
        .returning();

      return result.length <= 0 ? null : result[0];
    } catch (err) {
      throw new DatabaseException('failed to remove job by id', err, true);
    }
  }
}
