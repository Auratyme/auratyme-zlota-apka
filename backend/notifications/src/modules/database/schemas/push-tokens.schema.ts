import { pgTable, varchar, primaryKey } from 'drizzle-orm/pg-core';

export const pushTokensTable = pgTable(
  'push_tokens',
  {
    pushToken: varchar({ length: 255 }).notNull(),
    userId: varchar({ length: 255 }).notNull(),
  },
  (table) => [primaryKey({ columns: [table.pushToken, table.userId] })],
);
