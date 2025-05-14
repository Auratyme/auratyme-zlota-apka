import { ExpoPushMessage } from 'expo-server-sdk';

export type PushNotification = Omit<ExpoPushMessage, 'to'>;
