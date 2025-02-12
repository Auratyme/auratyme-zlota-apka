import { z } from 'zod';

export const schedulesUpdateOneSchema = z
  .object({
    name: z.string().max(50).optional(),
    description: z.string().max(500).optional(),
  })
  .strict();
