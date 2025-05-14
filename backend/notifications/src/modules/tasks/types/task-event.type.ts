import { Event } from '@/src/modules/event-source/types/event.type';

export type TaskEvent = Event<{
  task: {
    id: string;
    userId: string;
  };
}>;
