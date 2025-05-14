import { defineConfig } from 'drizzle-kit';

export default defineConfig({
  out: './drizzle',
  schema: './src/modules/database/schemas',
  dialect: 'postgresql',
  dbCredentials: {
    database: process.env.DB_NAME || '',
    host: process.env.DB_HOST || '',
    user: process.env.DB_USER || '',
    port: parseInt(process.env.DB_PORT || '5432'),
    password: process.env.DB_PASSWORD,
    ssl: false,
  },
  strict: true,
  verbose: true,
});
