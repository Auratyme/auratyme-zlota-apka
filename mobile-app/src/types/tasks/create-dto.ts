import { TaskStatus } from './status';

export type TaskCreateDto = {
  name: string,
  description?: string | null;
  status: TaskStatus;
  dueTo?: string | null;
  repeat?: string | null;
}
