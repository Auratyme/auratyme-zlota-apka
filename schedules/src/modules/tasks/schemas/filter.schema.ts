import { z } from 'zod';

import { datetimeFilterSchema, cronSchema } from '@app/common/schemas';

import { orderByTasksSchema } from './order-by.schema';
import { taskStatusFilterSchema } from './status.schema';

export const filterTasksSchema = z
  .object({
    orderBy: orderByTasksSchema.optional(),
    sortBy: z.enum(['asc', 'desc']).optional(),
    limit: z.number().int().min(0).optional(),
    page: z.number().int().min(0).optional(),
    where: z
      .object({
        name: z.string().max(50).optional(),
        status: taskStatusFilterSchema.optional(),
        repeat: cronSchema.optional(),
        dueTo: datetimeFilterSchema.optional(),
        createdAt: datetimeFilterSchema.optional(),
        updatedAt: datetimeFilterSchema.optional(),
      })
      .strict()
      .optional(),
  })
  .strict();
