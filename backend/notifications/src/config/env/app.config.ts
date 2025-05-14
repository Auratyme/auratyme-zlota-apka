export const appConfig = {
  port: parseInt(process.env.PORT || '3000'),
  serviceSecret: process.env.SERVICE_SECRET!,
};
