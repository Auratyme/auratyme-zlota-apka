import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';

import { configModuleConfig } from './config/modules';

import { JobsModule } from './modules/jobs/jobs.module';
import { DatabaseModule } from './modules/database/database.module';
import { TasksModule } from './modules/tasks/tasks.module';
import { EventsModule } from './modules/events/events.module';
import { SchedulesModule } from './modules/schedules/schedules.module';

import { AppController } from './app.controller';
import { AppService } from './app.service';

@Module({
  imports: [
    /* 3rd party modules */
    ConfigModule.forRoot(configModuleConfig),
    /* application modules */
    DatabaseModule,
    JobsModule,
    EventsModule,
    /* domain modules */
    TasksModule,
    SchedulesModule,
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
