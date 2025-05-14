import { TaskStatus } from './status.type';

export type Task = {
  id: string;
  name: string;
  description: string | null;
  status: TaskStatus;
  dueTo: string | null;
  repeat: string | null;
  createdAt: string;
  updatedAt: string;
  userId: string;
};
