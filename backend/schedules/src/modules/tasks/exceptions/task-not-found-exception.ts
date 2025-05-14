import { TaskException } from './task.exception';

export class TaskNotFoundException extends TaskException {
  constructor(taskId: string) {
    super(taskId, `task ${taskId} not found`, null);
  }
}
