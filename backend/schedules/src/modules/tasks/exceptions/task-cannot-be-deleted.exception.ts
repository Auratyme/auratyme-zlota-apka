import { TaskException } from './task.exception';

export class TaskCannotBeDeletedException extends TaskException {
  constructor(taskId: string) {
    super(taskId, `task ${taskId} cannot be deleted, because it belongs to schedule`, null);
  }
}
