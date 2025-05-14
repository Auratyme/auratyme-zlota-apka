import { Module, forwardRef } from '@nestjs/common';

import { AuthModule } from '@app/modules/auth/auth.module';

import { SchedulesTasksModule } from '../schedules-tasks/schedules-tasks.module';

import { TasksService } from './tasks.service';
import { TasksController } from './tasks.controller';
import { TasksRepository } from './tasks.repository';

@Module({
  imports: [AuthModule, forwardRef(() => SchedulesTasksModule)],
  controllers: [TasksController],
  providers: [TasksService, TasksRepository],
  exports: [TasksService, TasksRepository],
})
export class TasksModule {}
