import { AppException } from '@app/common/exceptions';

class JobException extends AppException {
  constructor(message: string, cause: unknown, isOperational = false) {
    super(message, cause, isOperational);
  }
}

export { JobException };
