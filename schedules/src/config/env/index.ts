import { authConfig as auth } from './auth.config';
import { dbConfig as db } from './db.config';
import { appConfig } from './app.config';

export const config = {
  ...appConfig,
  db,
  auth,
};
