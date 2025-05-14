import {
  Controller,
  Delete,
  Get,
  HttpStatus,
  InternalServerErrorException,
  NotFoundException,
  Param,
  ParseUUIDPipe,
  Post,
  Res,
  UseGuards,
  Body
} from '@nestjs/common';

import { Request, Response } from 'express';

import { SchedulesTasksService } from '../schedules-tasks.service';
import { UserData } from '@app/common/decorators';
import { ScheduleNotFoundException } from '@app/modules/schedules/exceptions';
import { AuthGuard } from '@app/modules/auth/auth.guard';
import { TaskNotFoundException } from '@app/modules/tasks/exceptions';
import { addTaskToScheduleSchema } from '../schemas';
import { ZodValidationPipe } from '@app/common/pipes';

@UseGuards(AuthGuard)
@Controller({
  path: 'schedules/:id/tasks',
  version: '1',
})
export class SchedulesTasksController {
  constructor(private readonly scheduleTasksService: SchedulesTasksService) { }

  @Get()
  async findTasksForSchedule(
    @Param('id', ParseUUIDPipe) scheduleId: string,
    @UserData() userData: Request['auth']['user'],
    @Res({ passthrough: true }) res: Response,
  ) {
    const userId = userData.id;

    try {
      const tasks = await this.scheduleTasksService.findTasksForSchedule(
        scheduleId,
        userId,
      );

      if (tasks.length <= 0) {
        res.status(HttpStatus.NO_CONTENT);
        return [];
      }

      return tasks;
    } catch (err) {
      if (err instanceof ScheduleNotFoundException) {
        throw new NotFoundException('Schedule not found');
      }

      throw new InternalServerErrorException(null, { cause: err });
    }
  }

  @Post()
  async addTaskToSchedule(
    @Param("id", ParseUUIDPipe) scheduleId: string,
    @UserData() userData: Request['auth']['user'],
    @Body(new ZodValidationPipe(addTaskToScheduleSchema)) body: typeof addTaskToScheduleSchema._type,
  ) {
    const userId = userData.id

    try {
      await this.scheduleTasksService.addTaskToSchedule(body.taskId, scheduleId, userId)
    } catch (err) {
      if (err instanceof ScheduleNotFoundException) {
        throw new NotFoundException('Schedule not found!')
      }

      if (err instanceof TaskNotFoundException) {
        throw new NotFoundException('Task not found!')
      }

      throw new InternalServerErrorException(null, { cause: err })
    }
  }

  @Delete()
  async removeAllTasksFromSchedule(
    @Param('id', ParseUUIDPipe) scheduleId: string,
    @UserData() userData: Request['auth']['user'],
  ) {
    const userId = userData.id

    try {
      await this.scheduleTasksService.removeAllTasksFromSchedule(scheduleId, userId)
    } catch (err) {
      if (err instanceof ScheduleNotFoundException) {
        throw new NotFoundException('Schedule not found');
      }

      throw new InternalServerErrorException(null, { cause: err });
    }
  }

  @Delete(':task_id')
  async removeTaskFromSchedule(
    @Param('id', ParseUUIDPipe) scheduleId: string,
    @Param('task_id', ParseUUIDPipe) taskId: string,
    @UserData() userData: Request['auth']['user'],
  ) {
    const userId = userData.id;

    try {
      await this.scheduleTasksService.removeTaskFromSchedule(
        taskId,
        scheduleId,
        userId,
      );
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
}
