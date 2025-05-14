import { AppException } from '@app/common/exceptions';

export class ScheduleException extends AppException {
  scheduleId: string;
  constructor(message: string, cause: unknown, scheduleId: string) {
    super(message, cause, true);

    this.scheduleId = scheduleId;
  }
}
