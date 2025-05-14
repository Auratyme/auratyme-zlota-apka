import { Module } from '@nestjs/common';
import { TasksService } from './tasks.service';
import { EventSourceModule } from '@/src/modules/event-source/event-source.module';

@Module({
  imports: [EventSourceModule],
  providers: [TasksService],
  exports: [TasksService],
})
export class TasksModule {}
