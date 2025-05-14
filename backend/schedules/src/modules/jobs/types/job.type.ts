import { JobType } from './job-type.type';

export type Job = {
  id: string;
  name: string;
  whenToExecute: string;
  type: JobType;
  attributes: Record<string, any> | null;
  callbackParams: any[];
};
