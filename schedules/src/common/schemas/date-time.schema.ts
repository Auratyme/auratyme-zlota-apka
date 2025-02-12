import { z } from 'zod';

import { DateTime } from 'luxon';

export const datetimeSchema = z.string().refine((str) => {
  return DateTime.fromISO(str).isValid;
});
