import {
  Injectable,
  CanActivate,
  ExecutionContext,
  UnauthorizedException,
  ForbiddenException,
  Logger,
} from '@nestjs/common';

import { ConfigService } from '@nestjs/config';

import { Request } from 'express';

import { AuthConfig } from '@app/common/types';

import { JwtService } from '@nestjs/jwt';

import { readFile } from 'node:fs/promises';

@Injectable()
export class AuthGuard implements CanActivate {
  private config: AuthConfig;
  private logger = new Logger(AuthGuard.name);

  constructor(
    private configService: ConfigService,
    private jwtService: JwtService,
  ) {
    this.config = this.configService.get<AuthConfig>('auth', { infer: true });
  }

  extractTokenFromHeader(req: Request): string | undefined {
    const token = req.headers['authorization']?.split(' ')[1];
    return token;
  }

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<Request>();

    const token = this.extractTokenFromHeader(request);

    if (token === undefined) {
      throw new UnauthorizedException();
    }

    const cert = await readFile(
      `${process.cwd()}/${this.config.publicKeyPath}`,
    );

    let payload;

    try {
      payload = await this.jwtService.verifyAsync(token, {
        issuer: this.config.oauthTenantDomain,
        audience: this.config.auratymeApiId,
        publicKey: cert,
      });
    } catch (err) {
      throw new ForbiddenException(null, err);
    }

    request.auth = {
      token: payload,
      user: {
        id: payload.sub,
      },
    };

    return true;
  }
}
