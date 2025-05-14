import { events } from '@/src/common/constants';

type EventName = 'task.repeated' | 'task.expired';

export type Event<T> = {
  eventName: EventName;
  payload: T;
};
