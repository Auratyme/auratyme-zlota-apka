import { TaskStatus } from './status.type.js';

export type CreateTaskDto = {
  name: string,
  userId: string;
  description?: string | null;
  status: TaskStatus;
  dueTo?: string | null;
  repeat?: string | null;
}
