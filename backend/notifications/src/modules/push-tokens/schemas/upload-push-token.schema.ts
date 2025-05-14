import { z } from 'zod';

export const uploadPushTokenSchema = z.object({
  pushToken: z.string().max(255),
});
