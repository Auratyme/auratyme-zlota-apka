import { z } from 'zod';

import { TaskStatus } from '@app/common/constants';

const taskStatusFilterSchema = z
  .array(z.nativeEnum(TaskStatus))
  .refine((items) => new Set(items).size === items.length, {
    message: 'Must be array of unique statuses',
  })
  .or(z.nativeEnum(TaskStatus));

export { taskStatusFilterSchema };
