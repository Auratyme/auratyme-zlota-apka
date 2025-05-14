import { FindOptions, DateTimeFilter } from '@app/common/types';

import { Task, TaskStatus } from '@app/modules/tasks/types';

export type TasksFindOptions = FindOptions<
  Partial<
    Omit<Task, 'createdAt' | 'updatedAt' | 'dueTo' | 'status'> & {
      dueTo?: DateTimeFilter;
      createdAt?: DateTimeFilter;
      updatedAt?: DateTimeFilter;
      status?: TaskStatus | TaskStatus[];
    }
  >,
  keyof Task
>;
