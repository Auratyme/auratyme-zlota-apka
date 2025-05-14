import {
  Injectable,
  OnApplicationShutdown,
  OnApplicationBootstrap,
} from '@nestjs/common';

import { JobsService } from './modules/jobs/jobs.service';
import { DatabaseService } from './modules/database/database.service';

@Injectable()
export class AppService
  implements OnApplicationShutdown, OnApplicationBootstrap
{
  constructor(
    private readonly jobsService: JobsService,
    private readonly database: DatabaseService,
  ) {}

  async onApplicationBootstrap() {
    await this.jobsService.scheduleExisting();
  }

  async onApplicationShutdown(signal?: string): Promise<void> {
    await this.jobsService.terminateAllJobs();

    await this.database.close();
  }
}
