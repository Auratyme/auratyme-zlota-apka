import { Module } from '@nestjs/common';
import { EventSourceService } from './event-source.service';

@Module({
  providers: [EventSourceService],
  exports: [EventSourceService],
})
export class EventSourceModule {}
