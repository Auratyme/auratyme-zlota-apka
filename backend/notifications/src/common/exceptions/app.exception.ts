export class AppException extends Error {
  isOperational: boolean;
  cause: unknown;

  constructor(message: string, cause: unknown, isOperational: boolean = false) {
    super(message);

    this.name = this.constructor.name;

    this.isOperational = isOperational;
    this.message = message;
    this.cause = cause;
  }
}
