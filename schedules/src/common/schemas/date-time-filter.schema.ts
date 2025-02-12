import { z } from 'zod';

import { datetimeSchema } from './date-time.schema';

export const datetimeFilterSchema = datetimeSchema.or(
  z.object({
    start: datetimeSchema.optional(),
    end: datetimeSchema.optional(),
  }),
);
