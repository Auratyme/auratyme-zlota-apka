import { Injectable } from '@nestjs/common';

import {
  TaskEvent,
  TaskJobName,
  TaskJobType,
  TaskStatus,
} from '@app/common/constants';

import { JobsService } from '@app/modules/jobs/jobs.service';

import { EventsService } from '@app/modules/events/events.service';

import {
  Task,
  CreateTaskDto,
  UpdateTaskDto,
  TasksFindOptions,
  TaskStatus as TaskStatusType,
  TaskEventPayload,
} from './types';

import { TasksRepository } from './tasks.repository';

@Injectable()
export class TasksService {
  constructor(
    private readonly tasksRepository: TasksRepository,
    private readonly jobsService: JobsService,
    private readonly eventsService: EventsService<TaskEventPayload>,
  ) {
    const dueToJobCallback = async (id: string, userId: string) => {
      this.eventsService.publish(TaskEvent.EXPIRED, { task: { id, userId } });

      return this.updateStatusToIf(id, [
        {
          to: TaskStatus.FAILED,
          if: TaskStatus.DONE,
          negate: true,
        },
      ]);
    };

    const repeatJobCallback = async (id: string, userId: string) => {
      this.eventsService.publish(TaskEvent.REPEATED, { task: { id, userId } });

      return this.updateStatusToIf(id, [
        {
          to: TaskStatus.FAILED,
          if: TaskStatus.DONE,
          negate: true,
        },
        {
          to: TaskStatus.NOT_STARTED,
          if: TaskStatus.DONE,
          negate: false,
        },
      ]);
    };

    jobsService.registerCallback(TaskJobName.DUE_TO, dueToJobCallback);
    jobsService.registerCallback(TaskJobName.REPEAT, repeatJobCallback);
  }

  private async updateStatusToIf(
    id: string,
    conditions: { to: TaskStatusType; if: TaskStatusType; negate: boolean }[],
  ): Promise<void> {
    const findByIdPromise = this.tasksRepository.findById(id);

    return findByIdPromise.then((task) => {
      if (!task) {
        return;
      }

      for (const condition of conditions) {
        const statusCondition = condition.negate
          ? task.status !== condition.if
          : task.status === condition.if;

        if (statusCondition) {
          this.tasksRepository.updateOne(id, task.userId, {
            status: condition.to,
          });
        }
      }
    });
  }

  private async createAndScheduleDueToJob(
    taskId: string,
    userId: string,
    taskDueTo: string,
  ): Promise<void> {
    return this.jobsService
      .create({
        whenToExecute: taskDueTo,
        name: TaskJobName.DUE_TO,
        type: TaskJobType.SINGLE,
        attributes: {
          taskId: taskId,
          userId: userId,
        },
        callbackParams: [taskId, userId],
      })
      .then(() => {});
  }

  private async createAndScheduleRepeatJob(
    taskId: string,
    userId: string,
    taskRepeat: string,
  ): Promise<void> {
    return this.jobsService
      .create({
        whenToExecute: taskRepeat,
        name: TaskJobName.REPEAT,
        type: TaskJobType.REPEATED,
        attributes: {
          taskId: taskId,
          userId: userId,
        },
        callbackParams: [taskId, userId],
      })
      .then(() => {});
  }

  private async rescheduleDueToJob(
    taskId: string,
    userId: string,
    taskDueTo: string,
  ): Promise<void> {
    return this.jobsService
      .updateMany(
        {
          where: {
            name: TaskJobName.DUE_TO,
            attributes: {
              taskId: taskId,
              userId: userId,
            },
          },
        },
        {
          whenToExecute: taskDueTo,
        },
      )
      .then((updatedJobs) => {
        if (updatedJobs.length <= 0) {
          return this.createAndScheduleDueToJob(taskId, userId, taskDueTo);
        }
      });
  }

  private async rescheduleRepeatJob(
    taskId: string,
    userId: string,
    taskRepeat: string,
  ): Promise<void> {
    return this.jobsService
      .updateMany(
        {
          where: {
            name: TaskJobName.REPEAT,
            attributes: {
              taskId: taskId,
              userId: userId,
            },
          },
        },
        {
          whenToExecute: taskRepeat,
        },
      )
      .then((updatedJobs) => {
        if (updatedJobs.length <= 0) {
          return this.createAndScheduleRepeatJob(taskId, userId, taskRepeat);
        }
      });
  }

  /**
   * Creates a new task.
   * @param {CreateTaskDto} newTask - The new task data.
   * @returns {Promise<Task>} A promise that resolves to the created task.
   * @throws {DatabaseException} If there is an error creating the task.
   */
  async create(newTask: CreateTaskDto): Promise<Task> {
    const createPromise = this.tasksRepository.create(newTask);

    createPromise.then((task) => {
      if (task.dueTo) {
        return this.createAndScheduleDueToJob(task.id, task.userId, task.dueTo);
      }

      if (task.repeat) {
        return this.createAndScheduleRepeatJob(
          task.id,
          task.userId,
          task.repeat,
        );
      }
    });

    return createPromise;
  }

  /**
   * Finds multiple tasks based on the provided options.
   * @param {TasksFindOptions} options - The options to filter tasks.
   * @returns {Promise<Task[]>} A promise that resolves to an array of tasks.
   * @throws {DatabaseException} If there is an error finding tasks.
   */
  async findMany(options: TasksFindOptions): Promise<Task[]> {
    return this.tasksRepository.findMany(options);
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
    return this.tasksRepository.findOne(id, userId);
  }

  /**
   * Updates a task by ID and user ID.
   * @param {string} id - The ID of the task.
   * @param {string} userId - The ID of the user.
   * @param {UpdateTaskDto} newTask - The new task data.
   * @returns {Promise<Task>} A promise that resolves to the updated task.
   * @throws {TaskNotFoundException} If the task is not found.
   * @throws {DatabaseException} If there is an error updating the task.
   */
  async updateOne(
    id: string,
    userId: string,
    newTask: UpdateTaskDto,
  ): Promise<Task> {
    try {
      const updatedTask = await this.tasksRepository.updateOne(
        id,
        userId,
        newTask,
      );

      if (updatedTask.dueTo) {
        await this.rescheduleDueToJob(
          updatedTask.id,
          updatedTask.userId,
          updatedTask.dueTo,
        );
      }

      if (updatedTask.repeat) {
        await this.rescheduleRepeatJob(
          updatedTask.id,
          updatedTask.userId,
          updatedTask.repeat,
        );
      }

      return updatedTask;
    } catch (err) {
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
      await this.tasksRepository.removeOne(id, userId);

      await this.jobsService.removeMany({
        where: {
          attributes: {
            taskId: id,
            userId: userId,
          },
        },
      });
    } catch (err) {
      throw err;
    }
  }
}
