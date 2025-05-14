import { z } from 'zod';

import { isValidCron } from 'cron-validator';

export const cronSchema = z.string().refine((str) => {
  return isValidCron(str, { seconds: true });
});
