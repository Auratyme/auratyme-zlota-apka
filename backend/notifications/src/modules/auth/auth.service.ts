import { AuthConfig } from '@/src/common/types';
import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { JwtService } from '@nestjs/jwt';

@Injectable()
export class AuthService {
  private authConfig: AuthConfig;
  private logger = new Logger(AuthService.name);

  constructor(
    private readonly configService: ConfigService,
    private readonly jwtService: JwtService,
  ) {
    this.authConfig = this.configService.get<AuthConfig>('auth', {
      infer: true,
    });
  }

  decodeAccessToken(token: string): any {
    return this.jwtService.decode(token, {
      json: true,
    });
  }

  async getAccessToken(): Promise<string> {
    return fetch(`${this.authConfig.oauthTenantDomain}/oauth/token`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        client_id: this.authConfig.oauthClientId,
        client_secret: this.authConfig.oauthClientSecret,
        audience: this.authConfig.auratymeApiId,
        grant_type: 'client_credentials',
      }),
    })
      .then((response) => {
        return response.json();
      })
      .then((json) => {
        const token = json['access_token'];
        this.logger.debug(json);
        return token as string;
      });
  }
}
