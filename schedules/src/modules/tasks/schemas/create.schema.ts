import { z } from 'zod';

import { TaskStatus } from '@app/common/constants';

import { datetimeSchema, cronSchema } from '@app/common/schemas';

export const createTaskSchema = z
  .object({
    name: z.string().max(50),
    description: z.string().max(500).optional(),
    status: z.nativeEnum(TaskStatus).default(TaskStatus.NOT_STARTED),
    dueTo: datetimeSchema.optional(),
    repeat: cronSchema.optional(),
    scheduleId: z.string().uuid().optional(),
  })
  .strict();
