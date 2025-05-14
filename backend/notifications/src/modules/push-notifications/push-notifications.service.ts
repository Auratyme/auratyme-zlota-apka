import { Injectable, Logger } from '@nestjs/common';
import {
  ExpoPushMessage,
  Expo,
  ExpoPushTicket,
  ExpoPushReceiptId,
} from 'expo-server-sdk';
import { PushTokensService } from '../push-tokens/push-tokens.service';
import { PushNotification } from './types';

@Injectable()
export class PushNotificationsService {
  private readonly logger = new Logger(PushNotificationsService.name);
  private readonly expo = new Expo();

  constructor(private readonly pushTokensService: PushTokensService) {}

  async sendPushNotifications(
    message: PushNotification,
    userId: string,
  ): Promise<void> {
    try {
      const pushTokens = (await this.pushTokensService.find(userId)).map(
        (val) => val.pushToken,
      );

      let messages: ExpoPushMessage[] = [];

      for (let pushToken of pushTokens) {
        if (!Expo.isExpoPushToken(pushToken)) {
          this.logger.error(`${pushToken} is not a valid push token`);
          continue;
        }

        messages.push({
          ...message,
          to: pushToken,
        });
      }

      let chunks = this.expo.chunkPushNotifications(messages);

      let tickets: ExpoPushTicket[] = [];

      for (let chunk of chunks) {
        let ticketChunk = await this.expo.sendPushNotificationsAsync(chunk);
        this.logger.debug(JSON.stringify(ticketChunk));
        tickets.push(...ticketChunk);
      }

      let receiptIds: ExpoPushReceiptId[] = [];

      for (let ticket of tickets) {
        if (ticket.status === 'ok') {
          receiptIds.push(ticket.id);
        }
      }

      let receiptIdChunks =
        this.expo.chunkPushNotificationReceiptIds(receiptIds);

      for (let chunk of receiptIdChunks) {
        let receipts = await this.expo.getPushNotificationReceiptsAsync(chunk);
        console.log(receipts);

        for (let receiptId in receipts) {
          let { status, details } = receipts[receiptId];

          if (status === 'ok') {
            continue;
          } else if (status === 'error') {
            console.error(`There was an error sending a notification`);

            if (details) {
              console.error('details: ', details);
            }
          }
        }
      }
    } catch (err) {
      console.error(err);
    }
  }
}
