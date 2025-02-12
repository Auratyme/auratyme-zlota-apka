import { FindOptions } from '@app/common/types';

import { Schedule } from '../schedule.type';

export type SchedulesFindManyOptions = FindOptions<
  {
    userId?: string;
  },
  keyof Schedule
>;
