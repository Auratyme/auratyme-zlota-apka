import { z } from 'zod';

export const schedulesCreateSchema = z
  .object({
    name: z.string().max(50),
    description: z.string().max(500).optional().nullable(),
  })
  .strict();
