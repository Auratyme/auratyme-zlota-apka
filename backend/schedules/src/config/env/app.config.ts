export const appConfig = {
  nodeEnv: process.env.NODE_ENV || 'production',
  port: parseInt(process.env.PORT || '3000'),
  notificationsServiceSecret: process.env.NOTIFICATIONS_SERVICE_SECRET!,
};
