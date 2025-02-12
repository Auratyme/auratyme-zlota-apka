import { Module, Global } from '@nestjs/common';

import { ScheduleModule } from '@nestjs/schedule';

import { JobsRepository } from './jobs.repository';
import { JobsService } from './jobs.service';

@Global()
@Module({
  imports: [ScheduleModule.forRoot()],
  providers: [JobsRepository, JobsService],
  exports: [JobsService],
})
export class JobsModule {}
