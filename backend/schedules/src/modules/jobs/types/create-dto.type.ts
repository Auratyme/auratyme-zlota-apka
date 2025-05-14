import { Job } from './job.type';

export type CreateJobDto = Omit<Job, 'id'>;
