import { Task } from './task';

export type TaskUpdateDto = Partial<Omit<Task, 'id' | 'updatedAt' | 'createdAt'>>;