import { TaskStatus } from "./status";

export type Task = {
  id: string;
  name: string;
  description: string | null;
  status: TaskStatus;
  dueTo: string | null;
  repeat: string | null;
  createdAt: string;
  updatedAt: string;
};
