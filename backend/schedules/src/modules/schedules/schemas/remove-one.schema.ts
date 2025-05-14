import { z } from 'zod';

export const schedulesRemoveOneSchema = z
  .object({
    options: z.object({
      forceDelete: z.object({
        deleteTasksPernamently: z.boolean().default(false)
      }).optional()
    }).optional()
  })
  .optional()
