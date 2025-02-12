import { z } from 'zod';

import { orderByTasksSchema } from './order-by.schema';

export const findTasksSchema = z
  .object({
    orderBy: orderByTasksSchema.optional(),
    sortBy: z.enum(['asc', 'desc']).optional(),
    limit: z
      .number({
        coerce: true,
      })
      .optional(),
    page: z
      .number({
        coerce: true,
      })
      .optional(),
  })
  .strict();
