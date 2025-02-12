import { pgTable, uuid, varchar, pgEnum, jsonb } from 'drizzle-orm/pg-core';

export const jobType = pgEnum('job_type', ['single', 'repetitive']);

export const jobsTable = pgTable('jobs', {
  id: uuid().primaryKey().defaultRandom().notNull(),
  name: varchar({ length: 255 }).notNull(),
  whenToExecute: varchar({ length: 255 }).notNull(),
  type: jobType().notNull(),
  attributes: jsonb().$type<Record<string, any> | null>(),
  callbackParams: jsonb().$type<any[]>().notNull(),
});
