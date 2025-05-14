import { z } from 'zod';

export const removeTaskSchema = z
  .object({
    options: z.object({
      forceDelete: z.boolean().default(false)
    }).optional()
  })
  .optional();
