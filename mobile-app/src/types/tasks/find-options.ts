import { Task } from "./task"

export type TaskFindOptions = {
  limit?: number,
  orderBy?: keyof Omit<Task, 'id' | 'description'>,
  sortBy?: 'asc' | 'desc',
  page?: number
}