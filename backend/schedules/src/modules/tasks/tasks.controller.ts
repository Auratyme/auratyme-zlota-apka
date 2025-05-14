import {
  Controller,
  Get,
  Post,
  Patch,
  Delete,
  Body,
  Res,
  Param,
  HttpStatus,
  NotFoundException,
  ParseUUIDPipe,
  Query,
  UseGuards,
  InternalServerErrorException,
  Sse,
  BadRequestException,
  Header,
  Headers,
} from '@nestjs/common';

import { Observable, filter, map } from 'rxjs';

import { Response, Request } from 'express';

import { ZodValidationPipe } from '@app/common/pipes';
import { UserData } from '@app/common/decorators';
import { TaskEvent } from '@app/common/constants';

import { AuthGuard } from '@app/modules/auth/auth.guard';

import { EventsService } from '@app/modules/events/events.service';

import {
  UpdateTaskDto,
  CreateTaskDto,
  Task,
  TasksFindOptions,
  TaskEventPayload,
} from './types';
import {
  createTaskSchema,
  filterTasksSchema,
  findTasksSchema,
  removeTaskSchema,
  tasksEventsSchema,
  updateTaskSchema,
} from './schemas';

import { TasksService } from './tasks.service';
import {
  TaskCannotBeDeletedException,
  TaskNotFoundException,
} from './exceptions';
import { SchedulesTasksService } from '../schedules-tasks/schedules-tasks.service';
import { ScheduleNotFoundException } from '../schedules/exceptions';
import { ConfigService } from '@nestjs/config';
import { AppConfig } from '@app/common/types';
import { JsonSocket } from '@nestjs/microservices';

@UseGuards(AuthGuard)
@Controller({
  path: 'tasks',
  version: '1',
})
export class TasksController {
  private appConfig: AppConfig;

  constructor(
    private readonly tasksService: TasksService,
    private readonly schedulesTasksService: SchedulesTasksService,
    private readonly eventService: EventsService<TaskEventPayload>,
    private readonly configService: ConfigService,
  ) {
    this.appConfig = this.configService.get<AppConfig>('app', {
      infer: true,
    });
  }

  @Sse('events')
  events(
    @UserData() userData: Request['auth']['user'],
    @Headers('notifications-service-secret')
    notificationsServiceSecret: string | undefined,
  ): Observable<unknown> {
    const userId = userData.id;

    if (
      notificationsServiceSecret === this.appConfig.notificationsServiceSecret
    ) {
      return this.eventService
        .consume(TaskEvent.ALL)
        .pipe(map((e) => JSON.stringify(e)));
    }

    return this.eventService.consume(TaskEvent.ALL).pipe(
      filter((payload) => payload.payload.task.userId === userId),
      map((payload) => JSON.stringify(payload)),
    );
  }

  @Get()
  async findMany(
    @UserData() userData: Request['auth']['user'],
    @Res({ passthrough: true }) res: Response,
    @Query(new ZodValidationPipe(findTasksSchema))
    query: typeof findTasksSchema._type,
  ): Promise<Task[]> {
    const { limit, page, sortBy, orderBy } = query;

    const userId = userData.id;

    const options: TasksFindOptions = {
      limit: limit || 10,
      page: page || 0,
      sortBy: sortBy || 'desc',
      orderBy: orderBy || 'createdAt',
      where: {
        userId: userId,
      },
    };

    try {
      const tasks = await this.tasksService.findMany(options);

      if (tasks.length === 0) {
        res.status(HttpStatus.NO_CONTENT);
        return [];
      }

      return tasks;
    } catch (err) {
      throw new InternalServerErrorException(null, { cause: err });
    }
  }

  @Get(':id')
  async findOne(
    @UserData() userData: Request['auth']['user'],
    @Param('id', ParseUUIDPipe) id: string,
  ): Promise<Task> {
    const userId = userData.id;

    try {
      const task = await this.tasksService.findOne(id, userId);

      return task;
    } catch (err) {
      if (err instanceof TaskNotFoundException) {
        throw new NotFoundException('Task not found!');
      }

      throw new InternalServerErrorException(null, { cause: err });
    }
  }

  @Post('/filters')
  async filter(
    @UserData() userData: Request['auth']['user'],
    @Res({ passthrough: true }) res: Response,
    @Body(new ZodValidationPipe(filterTasksSchema))
    body: typeof filterTasksSchema._type,
  ): Promise<Task[]> {
    const { limit, page, sortBy, orderBy } = body;
    const userId = userData.id;

    const filters: TasksFindOptions = {
      limit: limit || 10,
      page: page || 0,
      sortBy: sortBy || 'desc',
      orderBy: orderBy || 'createdAt',
      where: {
        name: body?.where?.name,
        userId: userId,
        status: body?.where?.status,
        dueTo: body?.where?.dueTo,
        createdAt: body?.where?.createdAt,
        updatedAt: body?.where?.updatedAt,
        repeat: body?.where?.repeat,
      },
    };

    try {
      const tasks = await this.tasksService.findMany(filters);

      if (tasks.length === 0) {
        res.status(HttpStatus.NO_CONTENT);
        return [];
      }

      return tasks;
    } catch (err) {
      throw new InternalServerErrorException(null, { cause: err });
    }
  }

  @Post()
  async create(
    @Body(new ZodValidationPipe(createTaskSchema))
    body: typeof createTaskSchema._type,
    @UserData() userData: Request['auth']['user'],
  ): Promise<Task> {
    const userId = userData.id;

    const newTask: CreateTaskDto = {
      name: body.name,
      description: body.description,
      dueTo: body.dueTo,
      repeat: body.repeat,
      status: body.status || 'not-started',
      userId: userId,
    };

    const scheduleId = body.scheduleId;

    try {
      const task = await this.tasksService.create(newTask);

      if (scheduleId) {
        this.schedulesTasksService.addTaskToSchedule(
          task.id,
          scheduleId,
          userId,
        );
      }

      return task;
    } catch (err) {
      if (err instanceof ScheduleNotFoundException) {
        throw new NotFoundException('Schedule not found');
      }

      if (err instanceof TaskNotFoundException) {
        throw new NotFoundException('Task not found');
      }

      throw new InternalServerErrorException(null, { cause: err });
    }
  }

  @Patch(':id')
  async updateOne(
    @UserData() userData: Request['auth']['user'],
    @Param('id', ParseUUIDPipe) id: string,
    @Body(new ZodValidationPipe(updateTaskSchema))
    body: typeof updateTaskSchema._type,
  ): Promise<Task> {
    const userId = userData.id;

    const newTask: UpdateTaskDto = {
      description: body.description,
      dueTo: body.dueTo,
      name: body.name,
      status: body.status,
      repeat: body.repeat,
    };

    const scheduleId = body.scheduleId;

    try {
      const updatedTask = await this.tasksService.updateOne(
        id,
        userId,
        newTask,
      );

      if (scheduleId) {
        await this.schedulesTasksService.addTaskToSchedule(
          updatedTask.id,
          scheduleId,
          userId,
        );
      }

      return updatedTask;
    } catch (err) {
      if (err instanceof TaskNotFoundException) {
        throw new NotFoundException('Task not found!');
      }

      if (err instanceof ScheduleNotFoundException) {
        throw new NotFoundException('Schedule not found!');
      }

      throw new InternalServerErrorException(null, { cause: err });
    }
  }

  @Delete(':id')
  async removeOne(
    @UserData() userData: Request['auth']['user'],
    @Param('id', ParseUUIDPipe) id: string,
    @Body(new ZodValidationPipe(removeTaskSchema))
    body: typeof removeTaskSchema._type,
  ): Promise<void> {
    const userId = userData.id;

    const forceDelete = body?.options?.forceDelete;

    try {
      if (forceDelete === true) {
        await this.schedulesTasksService.removeTaskFromAllSchedules(id, userId);
      }

      await this.tasksService.removeOne(id, userId);
    } catch (err) {
      if (err instanceof TaskNotFoundException) {
        throw new NotFoundException('Task not found!');
      }

      if (err instanceof TaskCannotBeDeletedException) {
        throw new BadRequestException(
          'Task cannot be deleted, because it belongs to schedule. Delete it from schedule first or use force delete option',
        );
      }

      throw new InternalServerErrorException(null, { cause: err });
    }
  }
}
