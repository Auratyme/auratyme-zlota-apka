import { RemoveOptions } from '@app/common/types';

import { Job } from '../job.type';

export type JobRemoveOptions = RemoveOptions<Partial<Job>>;
