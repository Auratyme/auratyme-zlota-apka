import { ScheduleException } from './schedule.exception';

export class ScheduleNotFoundException extends ScheduleException {
  constructor(scheduleId: string) {
    super(`schedule ${scheduleId} not found`, null, scheduleId);
  }
}
