export const dbConfig = {
  name: process.env.DB_NAME || 'notifications',
  port: parseInt(process.env.DB_PORT || '5432'),
  host: process.env.DB_HOST || 'notifications-db',
  user: process.env.DB_USER || 'admin',
  password: process.env.DB_PASSWORD || '',
  passwordFile: process.env.DB_PASSWORD_FILE || '',
};
