import { Module, forwardRef } from '@nestjs/common';

import { TasksModule } from '@app/modules/tasks/tasks.module';

import { SchedulesModule } from '@app/modules/schedules/schedules.module';

import { AuthModule } from '../auth/auth.module';

import { SchedulesTasksRepository } from './schedules-tasks.repository';
import { SchedulesTasksService } from './schedules-tasks.service';
import { SchedulesTasksController } from './controllers/schedules-tasks.controller';
import { TasksSchedulesController } from './controllers/tasks-schedules.controller';

@Module({
  imports: [
    forwardRef(() => TasksModule),
    forwardRef(() => SchedulesModule),
    AuthModule,
  ],
  controllers: [SchedulesTasksController, TasksSchedulesController],
  providers: [SchedulesTasksRepository, SchedulesTasksService],
  exports: [SchedulesTasksRepository, SchedulesTasksService],
})
export class SchedulesTasksModule {}
