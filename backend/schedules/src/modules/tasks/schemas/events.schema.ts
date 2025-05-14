import { z } from 'zod';

export const tasksEventsSchema = z
  .object({
    notificationsServiceSecret: z.string().max(500).optional(),
  })
  .optional();
