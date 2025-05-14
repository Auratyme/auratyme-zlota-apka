import { Test, TestingModule } from '@nestjs/testing';

import { JobsService } from '@app/modules/jobs/jobs.service';
import { EventsService } from '@app/modules/events/events.service';

import { CreateTaskDto, Task, UpdateTaskDto } from '../types';

import { TasksService } from '../tasks.service';
import { TasksRepository } from '../tasks.repository';

import {
  fakeTaskIds,
  fakeTaskNames,
  fakeTaskUserIds,
  fakeTasks,
} from './fake-data';

const mockTasksRepository = {
  findMany: jest.fn(),
  create: jest.fn(),
  updateOne: jest.fn(),
  findOne: jest.fn(),
  removeOne: jest.fn(),
};

const mockJobsService = {
  create: jest.fn(),
  schedule: jest.fn(),

  findMany: jest.fn(),
  findByAttribute: jest.fn(),
  findById: jest.fn(),

  updateMany: jest.fn(),
  updateById: jest.fn(),

  removeMany: jest.fn(),
  removeById: jest.fn(),

  terminateAllJobs: jest.fn(),
  scheduleExisting: jest.fn(),

  registerCallback: jest.fn(),
  getCallback: jest.fn(),
};

const mockEventsService = {
  publish: jest.fn(),
  consume: jest.fn(),
};

describe('TasksService', () => {
  let tasksService: TasksService;
  let tasksRepository: TasksRepository;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        TasksService,
        {
          provide: TasksRepository,
          useValue: mockTasksRepository,
        },
        {
          provide: JobsService,
          useValue: mockJobsService,
        },
        {
          provide: EventsService,
          useValue: mockEventsService,
        },
      ],
    }).compile();

    tasksService = module.get(TasksService);
    tasksRepository = module.get(TasksRepository);
  });

  describe('findMany', () => {
    describe('with no options provided', () => {
      it('should return an array of tasks', async () => {
        jest
          .spyOn(tasksRepository, 'findMany')
          .mockImplementation(async () => fakeTasks);

        expect(await tasksService.findMany({})).toStrictEqual(fakeTasks);
      });
    });

    describe('with otpions provided', () => {});
  });

  describe('findOne', () => {
    it('should return single task', async () => {
      const task: Task = fakeTasks[0]; // fake task 1

      jest
        .spyOn(tasksRepository, 'findOne')
        .mockImplementation(async () => task);

      expect(
        await tasksService.findOne(
          fakeTaskIds.FAKE_TASK_1_ID,
          fakeTaskUserIds.FAKE_TASK_1_USER_ID,
        ),
      ).toStrictEqual(task);
    });

    it('should return null', async () => {
      jest
        .spyOn(tasksRepository, 'findOne')
        .mockImplementation(async () => null);

      expect(
        await tasksService.findOne(
          fakeTaskIds.NON_EXISTENT_TASK_ID,
          fakeTaskUserIds.NON_EXISTENT_TASK_USER_ID,
        ),
      ).toStrictEqual(null);
    });
  });

  describe('create', () => {
    it('should return created task', async () => {
      const createDto: CreateTaskDto = {
        name: fakeTaskNames.FAKE_NEW_TASK_NAME,
        status: 'in-progress',
        description: null,
        dueTo: null,
        repeat: null,
        userId: fakeTaskUserIds.FAKE_NEW_TASK_USER_ID,
      };

      const createdTask: Task = {
        ...createDto,
        id: fakeTaskIds.FAKE_NEW_TASK_ID,
        createdAt: '2025-01-18T14:00:00Z',
        updatedAt: '2025-01-18T19:00:00Z',
      };

      jest
        .spyOn(tasksRepository, 'create')
        .mockImplementation(async () => createdTask);

      expect(await tasksService.create(createDto)).toStrictEqual(createdTask);
    });
  });

  describe('updateOne', () => {
    it('should return updated task', async () => {
      const updateDto: UpdateTaskDto = {};
      const id = fakeTaskIds.FAKE_TASK_2_ID;
      const userId = fakeTaskIds.FAKE_TASK_2_ID;

      const updatedTask: Task = {
        id,
        name: fakeTaskNames.FAKE_NEW_TASK_NAME,
        status: 'in-progress',
        description: null,
        dueTo: null,
        repeat: null,
        createdAt: '2025-01-18T14:00:00Z',
        updatedAt: '2025-01-18T19:00:00Z',
        userId,
        ...updateDto,
      };

      jest
        .spyOn(tasksRepository, 'updateOne')
        .mockImplementation(async () => updatedTask);

      expect(await tasksService.updateOne(id, userId, updateDto)).toStrictEqual(
        updatedTask,
      );
    });

    it('should return null', async () => {
      const id = fakeTaskIds.NON_EXISTENT_TASK_ID;
      const userId = fakeTaskUserIds.NON_EXISTENT_TASK_USER_ID;

      const updateDto: UpdateTaskDto = {};

      jest
        .spyOn(tasksRepository, 'updateOne')
        .mockImplementation(async () => null);

      expect(await tasksService.updateOne(id, userId, updateDto)).toStrictEqual(
        null,
      );
    });
  });

  describe('removeOne', () => {
    it('should return number of removed tasks', async () => {
      const id = fakeTaskIds.FAKE_TASK_5_ID;
      const userId = fakeTaskUserIds.FAKE_TASK_5_USER_ID;

      const removedCount = 1;

      jest
        .spyOn(tasksRepository, 'removeOne')
        .mockImplementation(async () => removedCount);

      expect(await tasksService.removeOne(id, userId)).toStrictEqual(
        removedCount,
      );
    });
  });
});
