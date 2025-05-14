import { Module } from '@nestjs/common';

import { JwtModule } from '@nestjs/jwt';

import { AuthGuard } from './auth.guard';

@Module({
  imports: [
    JwtModule.register({
      global: true,
    }),
  ],
  providers: [AuthGuard],
})
export class AuthModule {}
