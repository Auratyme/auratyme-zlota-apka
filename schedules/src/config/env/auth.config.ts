export const authConfig = {
  issuerBaseUrl:
    process.env.ISSUER_BASE_URL ||
    'http://localhost:9000/realms/effective-day-ai',

  baseUrl: process.env.BASE_URL || 'http://localhost',

  realmPublicKey: process.env.PUBLIC_KEY || '',
};
