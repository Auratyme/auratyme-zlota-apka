import {
  Injectable,
  OnModuleInit,
  OnModuleDestroy,
  Logger,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { AppConfig } from '@common/types';

import { TasksService } from '@modules/tasks/tasks.service';
import { PushNotificationsService } from '@modules/push-notifications/push-notifications.service';
import { AuthService } from '@modules/auth/auth.service';
import { PushNotification } from '@modules/push-notifications/types';
import { Task } from '../tasks/types';

@Injectable()
export class NotificationsService implements OnModuleDestroy, OnModuleInit {
  private appConfig: AppConfig;
  private logger = new Logger(NotificationsService.name);

  constructor(
    private readonly tasksService: TasksService,
    private readonly pushNotificationsService: PushNotificationsService,
    private readonly authService: AuthService,
    private readonly configService: ConfigService,
  ) {
    this.appConfig = this.configService.get<AppConfig>('app', { infer: true });
  }

  async onModuleInit() {
    try {
      const token =
        'eyJhbGciOiJSUzI1NiIsInR5cCI6ImF0K2p3dCIsImtpZCI6IkdQeGpta180am5jbHVOWEtkUE9BaSJ9.eyJpc3MiOiJodHRwczovL2Rldi1vcWFidDZtanF5N3Q4NnZjLnVzLmF1dGgwLmNvbS8iLCJzdWIiOiJnT1UxV0d6d1piS0NXRWM3bmpMTG1zcHM1WTg3RGtvTEBjbGllbnRzIiwiYXVkIjoiaHR0cHM6Ly9hcGkuYXVyYXR5bWUuY29tIiwiaWF0IjoxNzQ3MTc3NTI2LCJleHAiOjE3NDcyNjM5MjYsImp0aSI6InJTR2tqWGl2dnhRNnNNV3dDa3Z4aWkiLCJjbGllbnRfaWQiOiJnT1UxV0d6d1piS0NXRWM3bmpMTG1zcHM1WTg3RGtvTCJ9.CaS4PueOW8rPCqQtyAulmAFF4OvDw2X0lZhsQr3HtnRjpZzMZbgPpf1MRJg4dJHBflR76U9nSf7Kd3dlHFhfbq-WoFu2uMJA-zP-SfEcVB4mQpnTHcU787iE9LhW1HOZgYdJUloPaNi8fpQ2zc7Wu1AsqmCrnXNe6_HQlelkPEh7YagD0R8togqxILI4yoOGKFUNFGQuSfoJiAhgTws8fmsF4SZ-TOYYdV68Z8cfAO6BhnSP9PvRh1vs3WxFae8dSUUrZ4PDnSQDr_yzNcijeigFKhw-yDBJoAn6TU054DrnB27Gtvrjk1yNwLZ_r9BHIPexEQsM8ynOV3SyST2a7A';

      this.tasksService.events(token, this.appConfig.serviceSecret).subscribe({
        next: async (event) => {
          let title: string = `Task ${event.payload.task.id} expired!`;

          const notification: PushNotification = {
            title: title,
            sound: 'default',
            data: event,
            priority: 'high',
            interruptionLevel: 'active',
          };

          this.pushNotificationsService.sendPushNotifications(
            notification,
            event.payload.task.userId,
          );
        },

        error: (err) => {
          console.error(err);
        },
      });
    } catch (err) {
      console.error(err);
    }
  }

  async onModuleDestroy() {}
}
