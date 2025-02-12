import { pgTable, uuid, varchar, timestamp } from 'drizzle-orm/pg-core';

export const schedulesTable = pgTable('schedules', {
  id: uuid().defaultRandom().notNull().primaryKey(),
  name: varchar({ length: 50 }).notNull(),
  description: varchar({ length: 500 }),
  userId: uuid().notNull(),
  createdAt: timestamp().notNull().defaultNow(),
  updatedAt: timestamp()
    .notNull()
    .defaultNow()
    .$onUpdateFn(() => new Date()),
});
