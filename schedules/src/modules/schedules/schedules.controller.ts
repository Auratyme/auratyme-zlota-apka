import {
  Controller,
  Delete,
  Get,
  InternalServerErrorException,
  ParseUUIDPipe,
  Patch,
  Post,
  UseGuards,
  Param,
  Body,
  Query,
  Res,
  HttpStatus,
  NotFoundException,
} from '@nestjs/common';

import { Request, Response } from 'express';

import { UserData } from '@app/common/decorators';

import { ZodValidationPipe } from '@app/common/pipes';

import { AuthGuard } from '@app/modules/auth/auth.guard';

import {
  Schedule,
  CreateScheduleDto,
  UpdateScheduleDto,
  SchedulesFindManyOptions,
} from './types';

import {
  schedulesCreateSchema,
  schedulesFindManySchema,
  schedulesUpdateOneSchema,
} from './schemas';

import { ScheduleNotFoundException } from './exceptions';

import { SchedulesService } from './schedules.service';

@UseGuards(AuthGuard)
@Controller({
  path: 'schedules',
  version: '1',
})
export class SchedulesController {
  constructor(private readonly schedulesService: SchedulesService) {}

  @Get()
  async findMany(
    @UserData() userData: Request['auth']['user'],
    @Query(new ZodValidationPipe(schedulesFindManySchema))
    query: typeof schedulesFindManySchema._type,
    @Res({ passthrough: true }) response: Response,
  ): Promise<Schedule[]> {
    const userId = userData.id;
    const { limit, orderBy, page, sortBy } = query;
    const options: SchedulesFindManyOptions = {
      limit,
      orderBy,
      page,
      sortBy,
      where: {
        userId,
      },
    };

    try {
      const schedules = await this.schedulesService.findMany(options);

      if (schedules.length <= 0) {
        response.status(HttpStatus.NO_CONTENT);
        return [];
      }

      return schedules;
    } catch (err) {
      throw new InternalServerErrorException(null, { cause: err });
    }
  }

  @Get(':id')
  async findOne(
    @UserData() userData: Request['auth']['user'],
    @Param('id', ParseUUIDPipe) id: string,
  ): Promise<Schedule | null> {
    const userId = userData.id;

    try {
      const schedule = await this.schedulesService.findOne(id, userId);

      return schedule;
    } catch (err) {
      if (err instanceof ScheduleNotFoundException) {
        throw new NotFoundException('Schedule not found!');
      }

      throw new InternalServerErrorException(null, { cause: err });
    }
  }

  @Post()
  async create(
    @UserData() userData: Request['auth']['user'],
    @Body(new ZodValidationPipe(schedulesCreateSchema))
    body: typeof schedulesCreateSchema._type,
  ): Promise<Schedule> {
    const userId = userData.id;

    const createDto: CreateScheduleDto = {
      ...body,
      userId,
      description: body.description || null,
    };

    try {
      return this.schedulesService.create(createDto);
    } catch (err) {
      throw new InternalServerErrorException(null, { cause: err });
    }
  }

  @Patch(':id')
  async updateOne(
    @UserData() userData: Request['auth']['user'],
    @Body(new ZodValidationPipe(schedulesUpdateOneSchema))
    body: typeof schedulesUpdateOneSchema._type,
    @Param('id', ParseUUIDPipe) id: string,
  ): Promise<void> {
    const userId = userData.id;
    const updateDto: UpdateScheduleDto = {
      ...body,
      description: body.description || null,
      name: body.name || null,
    };

    try {
      await this.schedulesService.updateOne(id, userId, updateDto);
    } catch (err) {
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
  ): Promise<void> {
    const userId = userData.id;

    try {
      await this.schedulesService.removeOne(id, userId);
    } catch (err) {
      if (err instanceof ScheduleNotFoundException) {
        throw new NotFoundException('Schedule not found!');
      }

      throw new InternalServerErrorException(null, { cause: err });
    }
  }
}
