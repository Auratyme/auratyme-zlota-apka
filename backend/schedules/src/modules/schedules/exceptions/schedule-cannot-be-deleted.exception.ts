import { ScheduleException } from './schedule.exception';

export class ScheduleCannotBeDeletedException extends ScheduleException {
  constructor(scheduleId: string) {
    super(`schedule ${scheduleId} cannot be deleted, because it is not empty`, null, scheduleId);
  }
}
