import { Task } from './task.type.js';

export type CreateTaskDto = Omit<Task, 'id' | 'createdAt' | 'updatedAt'>;
