import { Module } from '@nestjs/common';
import { NotificationsService } from './notifications.service';
import { PushNotificationsModule } from '../push-notifications/push-notifications.module';
import { TasksModule } from '../tasks/tasks.module';
import { AuthModule } from '../auth/auth.module';

@Module({
  imports: [PushNotificationsModule, TasksModule, AuthModule],
  providers: [NotificationsService],
  exports: [NotificationsService],
})
export class NotificationsModule {}
