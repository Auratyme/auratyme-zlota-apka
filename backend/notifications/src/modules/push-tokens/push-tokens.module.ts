import { Module } from '@nestjs/common';
import { PushTokensController } from './push-tokens.controller';
import { PushTokensRepository } from './push-tokens.repository';
import { PushTokensService } from './push-tokens.service';
import { AuthModule } from '../auth/auth.module';

@Module({
  imports: [AuthModule],
  controllers: [PushTokensController],
  providers: [PushTokensRepository, PushTokensService],
  exports: [PushTokensService],
})
export class PushTokensModule {}
