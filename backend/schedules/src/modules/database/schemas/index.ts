import { TaskStatusEnum, tasksTable } from './tasks.schema';

import { jobType, jobsTable } from './jobs.schema';

import { schedulesTable } from './schedules.schema';

import {
  schedulesTasksTable,
  schedulesRelations,
  schedulesTasksRelations,
  tasksRelations,
} from './schedules-tasks.schema';

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
  schedulesTasksTable,
  schedulesTasksRelations,
};
