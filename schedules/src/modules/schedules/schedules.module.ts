import { Module, forwardRef } from '@nestjs/common';

import { AuthModule } from '../auth/auth.module';

import { SchedulesTasksModule } from '../schedules-tasks/schedules-tasks.module';

import { SchedulesService } from './schedules.service';
import { SchedulesController } from './schedules.controller';
import { SchedulesRepository } from './schedules.repository';

@Module({
  imports: [AuthModule, forwardRef(() => SchedulesTasksModule)],
  controllers: [SchedulesController],
  providers: [SchedulesRepository, SchedulesService],
  exports: [SchedulesService, SchedulesRepository],
})
export class SchedulesModule {}
