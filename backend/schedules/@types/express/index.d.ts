import { JwtPayload } from 'jsonwebtoken';

declare global {
  namespace Express {
    interface Request {
      auth: {
        token: JwtPayload;
        user: {
          id: string;
        };
      };
    }
  }
}
