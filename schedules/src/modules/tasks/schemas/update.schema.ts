import { z } from 'zod';

import { TaskStatus } from '@app/common/constants';

import { cronSchema, datetimeSchema } from '@app/common/schemas';

export const updateTaskSchema = z
  .object({
    name: z.string().max(50).optional(),
    description: z.string().max(500).optional(),
    status: z.nativeEnum(TaskStatus).optional(),
    dueTo: datetimeSchema.optional(),
    repeat: cronSchema.optional(),
  })
  .strict();
