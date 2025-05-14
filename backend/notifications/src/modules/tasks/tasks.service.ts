import { Injectable } from '@nestjs/common';
import { Observable } from 'rxjs';
import { Task, TaskEvent } from './types';
import { EventSourceService } from '../event-source/event-source.service';

@Injectable()
export class TasksService {
  constructor(private readonly eventSource: EventSourceService) {}

  events(
    accessToken: string,
    notificationsServiceSecret: string,
  ): Observable<TaskEvent> {
    this.eventSource.connect('http://schedules:3000/v1/tasks/events', {
      authorization: `Bearer ${accessToken}`,
      'notifications-service-secret': notificationsServiceSecret,
    });

    return this.eventSource.on('message') as Observable<TaskEvent>;
  }

  findOne(accessToken: string, id: string): Promise<Task> {
    const findOnePromise = fetch(`http://schedules:3000/v1/tasks/${id}`, {
      method: 'GET',
      headers: {
        authorization: `Bearer ${accessToken}`,
        'content-type': 'application/json',
      },
    }).then((response) => {
      if (!response.ok) {
        throw new Error(response.statusText);
      }

      return response.json();
    });

    return findOnePromise;
  }
}
