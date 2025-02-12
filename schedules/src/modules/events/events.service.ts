import { Injectable, Logger } from '@nestjs/common';
import { EventEmitter2 } from '@nestjs/event-emitter';

import { fromEvent, Observable } from 'rxjs';

import { Event } from './types';

@Injectable()
export class EventsService<Payload> {
  private logger = new Logger(EventsService.name);

  constructor(readonly emitter: EventEmitter2) {}

  publish(eventName: string, payload: Payload): void {
    this.emitter.emit(eventName, {
      eventName,
      payload,
    } as Event<Payload>);

    this.logger.verbose(`event ${eventName} emitted`);
  }

  consume(eventName: string): Observable<Event<Payload>> {
    return fromEvent(this.emitter, eventName) as Observable<Event<Payload>>;
  }
}
