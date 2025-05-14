import {
  Injectable,
  Logger,
  OnModuleDestroy,
  OnModuleInit,
} from '@nestjs/common';
import { EventSource } from 'eventsource';
import { fromEvent, Observable, map } from 'rxjs';

@Injectable()
export class EventSourceService implements OnModuleDestroy, OnModuleInit {
  private eventSource: EventSource | null = null;
  private readonly logger = new Logger(EventSourceService.name);
  private url: string | null = null;

  constructor() {}

  connect(url: string, headers?: Record<string, string>) {
    this.url = url;

    this.eventSource = new EventSource(url, {
      fetch: (input, init) =>
        fetch(input, {
          ...init,
          headers: {
            ...init?.headers,
            ...headers,
          },
        }),
    });

    this.eventSource.addEventListener('error', (e) => {
      this.logger.error(e.message);
    });

    this.eventSource.addEventListener('open', (e) => {
      this.logger.debug(`listening for events on ${url}`);
    });
  }

  close() {
    this.eventSource?.close();

    if (this.eventSource !== null) {
      this.logger.debug(`connection with ${this.url} closed!`);
    }

    this.eventSource = null;
  }

  on(eventName: string): Observable<unknown> {
    if (this.eventSource === null) {
      throw new Error(
        'cannot listen for events, when connection is not established',
      );
    }

    return fromEvent(this.eventSource, eventName).pipe(
      map((e: MessageEvent<string>) => JSON.parse(e.data)),
    );
  }

  onModuleInit() {}

  onModuleDestroy() {
    this.eventSource?.close();

    if (this.eventSource !== null) {
      this.logger.debug(`connection with ${this.url} closed!`);
    }

    this.eventSource = null;
  }
}
