import { pgTable, uuid, primaryKey } from 'drizzle-orm/pg-core';

import { tasksTable } from './tasks.schema';
import { schedulesTable } from './schedules.schema';
import { relations } from 'drizzle-orm';

export const scheduleTasksTable = pgTable(
  'schedule_tasks',
  {
    taskId: uuid()
      .defaultRandom()
      .notNull()
      .references(() => tasksTable.id),
    scheduleId: uuid()
      .defaultRandom()
      .notNull()
      .references(() => schedulesTable.id),
  },
  (t) => [primaryKey({ columns: [t.scheduleId, t.taskId] })],
);

export const tasksRelations = relations(tasksTable, ({ many }) => ({
  tasksToSchedules: many(scheduleTasksTable),
}));

export const schedulesRelations = relations(schedulesTable, ({ many }) => ({
  tasksToSchedules: many(scheduleTasksTable),
}));

export const schedulesTasksRelations = relations(
  scheduleTasksTable,
  ({ one }) => ({
    task: one(tasksTable, {
      fields: [scheduleTasksTable.taskId],
      references: [tasksTable.id],
    }),
    schedule: one(schedulesTable, {
      fields: [scheduleTasksTable.scheduleId],
      references: [schedulesTable.id],
    }),
  }),
);
