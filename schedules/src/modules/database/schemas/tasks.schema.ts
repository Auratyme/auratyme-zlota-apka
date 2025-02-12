import { pgTable, uuid, varchar, timestamp, pgEnum } from 'drizzle-orm/pg-core';

const taskStatuses = ['not-started', 'in-progress', 'done', 'failed'] as const;

export const TaskStatusEnum = pgEnum('task_status', taskStatuses);

export const tasksTable = pgTable('tasks', {
  id: uuid().primaryKey().defaultRandom().notNull(),
  name: varchar({ length: 50 }).notNull(),
  description: varchar({ length: 500 }),
  status: TaskStatusEnum().notNull().default('not-started'),
  dueTo: timestamp(),
  repeat: varchar({ length: 50 }),
  userId: uuid().notNull(),
  createdAt: timestamp().notNull().defaultNow(),
  updatedAt: timestamp()
    .notNull()
    .defaultNow()
    .$onUpdateFn(() => new Date()),
});
