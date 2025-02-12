import {
  Injectable,
  CanActivate,
  ExecutionContext,
  UnauthorizedException,
  ForbiddenException,
  Logger,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { Observable } from 'rxjs';

import { Request } from 'express';

import { getPublicKeyInPemFormat } from '@app/common/utils';

import { AuthConfig } from './types';

import { AuthService } from './auth.service';
import { JwtPayload } from 'jsonwebtoken';

@Injectable()
export class AuthGuard implements CanActivate {
  private config: AuthConfig;
  private logger = new Logger(AuthGuard.name);

  constructor(
    private authService: AuthService,
    private configService: ConfigService,
  ) {
    this.config = this.configService.get<AuthConfig>('auth', { infer: true });
  }

  canActivate(
    context: ExecutionContext,
  ): boolean | Promise<boolean> | Observable<boolean> {
    const request = context.switchToHttp().getRequest<Request>();
    const publicKey = getPublicKeyInPemFormat(this.config.realmPublicKey);

    let token: string;

    try {
      token = this.authService.retrieveToken(request);
    } catch (err) {
      throw new UnauthorizedException();
    }

    let tokenPayload: JwtPayload;

    try {
      tokenPayload = this.authService.verifyAndDecodeToken(
        token,
        publicKey.toString(),
      );
    } catch (err) {
      throw new ForbiddenException();
    }

    request.auth = {
      token: tokenPayload,
      user: {
        id: tokenPayload.sub || '',
        name: tokenPayload['preferred_username'],
      },
    };

    this.logger.log(`user ${tokenPayload['preferred_username']} authorized`);

    return true;
  }
}
