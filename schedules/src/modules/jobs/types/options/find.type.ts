import { FindOptions } from '@app/common/types';

import { Job } from '../job.type';

export type JobFindOptions = FindOptions<Partial<Job>, keyof Job>;
