import { UpdateOptions } from '@app/common/types';

import { Job } from '../job.type';

export type JobUpdateOptions = UpdateOptions<Partial<Job>>;
