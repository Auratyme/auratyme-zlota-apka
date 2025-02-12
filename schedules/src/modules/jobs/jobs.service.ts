import { Injectable, Logger } from '@nestjs/common';
import { SchedulerRegistry, Timeout } from '@nestjs/schedule';

import { CronJob, CronTime } from 'cron';

import { convertToISOLuxonDate } from '@app/common/utils';

import { JobException } from './execeptions';

import {
  CreateJobDto,
  Job,
  JobCallback,
  JobFindOptions,
  JobRemoveOptions,
  JobUpdateOptions,
  UpdateJobDto,
} from './types';

import { JobsRepository } from './jobs.repository';

/**
 * @class JobsService
 * allows you to manage cron jobs.
 * @description
 * Every job has it's own internal data, custom attributes and parameters that will be passed to callback. Instead of passing callback everytime you want to create / schedule job you register callback(s) immediately and each time, you want to create / schedule job you only pass parameters
 */
@Injectable()
export class JobsService {
  private callbackMap: Map<string, JobCallback>;
  private logger = new Logger(JobsService.name);

  constructor(
    private jobsRepository: JobsRepository,
    private schedulerRegistry: SchedulerRegistry,
  ) {
    this.callbackMap = new Map<string, JobCallback>();
  }

  /**
   * @param jobName name of job to associate callback with
   * @param callback actual callback
   * @description inserts callback to callback map for later use
   */
  registerCallback(jobName: string, callback: JobCallback): void {
    this.callbackMap.set(jobName, callback);
    this.logger.verbose(`callback for ${jobName} job registered`);
  }

  /**
   *
   * @param jobName job name that callback is associated with
   * @returns callback
   * @throws JobException
   * @description retrieves callback from callback map or throws error
   */
  getCallback(jobName: string): JobCallback {
    const callback = this.callbackMap.get(jobName);

    if (!callback) {
      throw new JobException('callback was not registered!', undefined, true);
    }

    return callback;
  }

  /**
   *
   * @async
   * @param newJob job data needed for creation
   * @returns created job
   * @description creates job in database, retrieves callback from callback map and then starts job
   */
  async create(newJob: CreateJobDto): Promise<Job> {
    const createPromise = this.jobsRepository.create(newJob);

    createPromise.then((job) => {
      const callback = this.getCallback(job.name);
      const cronTime =
        convertToISOLuxonDate(job.whenToExecute) || job.whenToExecute;

      const cronJob = new CronJob(cronTime, () => {
        callback(...job.callbackParams)
          .then(() => {
            this.logger.log(`job with id ${job.id} executed`);
          })
          .catch((err) => {
            this.logger.error(
              new JobException('error while executing callback', err, true),
            );
          });
      });

      this.schedulerRegistry.addCronJob(job.id, cronJob);

      try {
        cronJob.start();
      } catch (err) {
        this.logger.error(new JobException('error while starting', err, true));
      }

      this.logger.verbose(
        `job with id ${job.id} created, execution: ${cronTime}`,
      );
    });

    return createPromise;
  }

  /**
   *
   * @async
   * @param id id of job to start
   * @description retrieves job from database by id and starts it
   */
  async schedule(id: string): Promise<void> {
    return this.jobsRepository.findById(id).then((job) => {
      if (!job) {
        return;
      }

      const callback = this.getCallback(job.name);

      const cronTime =
        convertToISOLuxonDate(job.whenToExecute) || job.whenToExecute;

      const cronJob = new CronJob(cronTime, () => {
        callback(...job.callbackParams)
          .then(() => {
            this.logger.log(`job with id ${job.id} executed`);
          })
          .catch((err) => {
            this.logger.error(
              new JobException('error while executing callback', err, true),
            );
          });
      });

      this.schedulerRegistry.addCronJob(job.id, cronJob);

      try {
        cronJob.start();
      } catch (err) {
        this.logger.error(new JobException('error while starting', err, true));
      }

      this.logger.verbose(`job with id ${job.id} scheduled`);
    });
  }

  /**
   *
   * @async
   * @param options search filters
   * @returns found jobs
   * @description finds jobs by filters
   */
  async findMany(options: JobFindOptions): Promise<Job[]> {
    const findManyPromise = this.jobsRepository.findMany(options);

    return findManyPromise;
  }

  /**
   *
   * @async
   * @param attributes job attributes to search by
   * @returns found jobs
   * @description finds jobs by attributes
   */
  async findByAttribute(attributes: Record<string, any>): Promise<Job[]> {
    const findByAttributePromise =
      this.jobsRepository.findByAttributes(attributes);

    return findByAttributePromise;
  }

  /**
   *
   * @async
   * @param id job's id
   * @returns found job
   * @description finds job by id
   */
  async findById(id: string): Promise<Job | null> {
    const findByIdPromise = this.jobsRepository.findById(id);

    return findByIdPromise;
  }

  /**
   *
   * @async
   * @param options which jobs to update
   * @param newJob which fields to update
   * @returns array of updated jobs
   * @description updates job in database and then start's it if whenToExecute was changed
   */
  async updateMany(
    options: JobUpdateOptions,
    newJob: UpdateJobDto,
  ): Promise<Job[]> {
    const updateManyPromise = this.jobsRepository.updateMany(options, newJob);

    updateManyPromise.then((jobs) => {
      for (const job of jobs) {
        const cronJob = this.schedulerRegistry.getCronJob(job.id);
        const cronTime = new CronTime(
          convertToISOLuxonDate(job.whenToExecute) || job.whenToExecute,
        );

        cronJob.setTime(cronTime);

        this.logger.verbose(`job with id ${job.id} updated`);
      }
    });

    return updateManyPromise;
  }

  /**
   *
   * @async
   * @param id job's id
   * @param newJob which field to update
   * @returns updated Job or nothing
   * @description updates job in database and then start's it if whenToExecute was changed
   */
  async updateById(id: string, newJob: UpdateJobDto): Promise<Job | null> {
    const updateByIdPromise = this.jobsRepository.updateById(id, newJob);

    updateByIdPromise.then((job) => {
      if (!job) return;

      const cronJob = this.schedulerRegistry.getCronJob(job.id);
      const cronTime = new CronTime(
        convertToISOLuxonDate(job.whenToExecute) || job.whenToExecute,
      );

      cronJob.setTime(cronTime);

      this.logger.verbose(`job with id ${job.id} updated`);
    });

    return updateByIdPromise;
  }

  /**
   *
   * @async
   * @param options which jobs to remove
   * @returns array ofremoved jobs
   * @description removes jobs from database and stops them
   */
  async removeMany(options: JobRemoveOptions): Promise<Job[]> {
    const removeManyPromise = this.jobsRepository.removeMany(options);

    removeManyPromise.then((jobs) => {
      for (const job of jobs) {
        this.schedulerRegistry.deleteCronJob(job.id);

        this.logger.verbose(`job with id ${job.id} removed`);
      }
    });

    return removeManyPromise;
  }

  /**
   *
   * @async
   * @param id job's id
   * @returns removed job or nothing
   * @description removes job from database and stops it
   */
  async removeById(id: string): Promise<Job | null> {
    const removeByIdPromise = this.jobsRepository.removeById(id);

    removeByIdPromise.then((job) => {
      if (!job) return;

      this.schedulerRegistry.deleteCronJob(job.id);

      this.logger.verbose(`job with id ${job.id} removed`);
    });

    return removeByIdPromise;
  }

  /**
   * @async
   * @description terminates all jobs
   */
  async terminateAllJobs(): Promise<void> {
    return this.jobsRepository.findMany({}).then((jobs) => {
      for (const job of jobs) {
        this.schedulerRegistry.deleteCronJob(job.id);
      }

      this.logger.log('All jobs terminated');
    });
  }

  /**
   * @async
   * @description schedules all existing jobs second after application startup
   */
  async scheduleExisting(): Promise<void> {
    return this.jobsRepository.findMany({}).then((jobs) => {
      for (const job of jobs) {
        this.schedule(job.id);
      }

      this.logger.log('All existing jobs scheduled');
    });
  }
}
