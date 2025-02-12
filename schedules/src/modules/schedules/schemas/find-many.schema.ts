import { z } from 'zod';

import { schedulesOrderBySchema } from './order-by.schema';

export const schedulesFindManySchema = z
  .object({
    orderBy: schedulesOrderBySchema.optional().default('createdAt'),
    sortBy: z.enum(['asc', 'desc']).optional().default('desc'),
    limit: z.number({ coerce: true }).positive().optional().default(10),
    page: z.number({ coerce: true }).nonnegative().optional().default(0),
  })
  .strict();
