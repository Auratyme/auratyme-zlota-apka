import { TaskStatusEnum, tasksTable } from './tasks.schema';

import { jobType, jobsTable } from './jobs.schema';

import { schedulesTable } from './schedules.schema';

import {
  scheduleTasksTable,
  schedulesRelations,
  schedulesTasksRelations,
  tasksRelations,
} from './schedule-tasks.schema';

export {
  TaskStatusEnum,
  tasksTable,
  tasksRelations,
  // --------
  jobType,
  jobsTable,
  // --------
  schedulesTable,
  schedulesRelations,
  // --------
  scheduleTasksTable,
  schedulesTasksRelations,
};
