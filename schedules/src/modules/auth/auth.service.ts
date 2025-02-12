import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { JwtPayload, verify, VerifyOptions } from 'jsonwebtoken';

import { AuthConfig } from './types';
import { Request } from 'express';

@Injectable()
export class AuthService {
  private config: AuthConfig;

  constructor(private configService: ConfigService) {
    this.config = this.configService.get<AuthConfig>('auth', { infer: true });
  }

  retrieveToken(request: Request): string {
    const token = request.headers['authorization']?.split(' ')[1];

    if (!token) {
      throw new Error('You must provide token!');
    }

    return token;
  }

  verifyAndDecodeToken(token: string, publicKey: string): JwtPayload {
    const options: VerifyOptions = {
      issuer: this.config.issuerBaseUrl,
      audience: this.config.baseUrl,
      algorithms: ['RS256'],
    };

    let tokenPayload;

    try {
      tokenPayload = verify(token, publicKey, options);
    } catch (err) {
      throw err;
    }

    return tokenPayload;
  }
}
