import { Job } from './job.type';

export type UpdateJobDto = Omit<Partial<Job>, 'id'>;
