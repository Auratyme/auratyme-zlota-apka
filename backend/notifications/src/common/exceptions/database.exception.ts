import { AppException } from './app.exception';

export class DatabaseException extends AppException {
  constructor(message: string, cause: unknown, isOperational: boolean) {
    super(message, cause, isOperational);
  }
}
