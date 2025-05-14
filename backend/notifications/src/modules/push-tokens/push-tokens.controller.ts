import {
  Body,
  Controller,
  Delete,
  Get,
  HttpCode,
  HttpStatus,
  InternalServerErrorException,
  NotImplementedException,
  Post,
  UseGuards,
} from '@nestjs/common';
import { Request } from 'express';
import { AuthGuard } from '@/src/modules/auth/auth.guard';
import { ZodValidationPipe } from '@/src/common/pipes';
import { uploadPushTokenSchema } from './schemas';
import { UserData } from '@/src/common/decorators';
import { PushTokensService } from './push-tokens.service';

@UseGuards(AuthGuard)
@Controller({
  path: '/push-tokens',
})
export class PushTokensController {
  constructor(private readonly pushTokensService: PushTokensService) {}

  @Post()
  @HttpCode(HttpStatus.CREATED)
  async upload(
    @Body(new ZodValidationPipe(uploadPushTokenSchema))
    body: typeof uploadPushTokenSchema._type,
    @UserData() user: Request['auth']['user'],
  ) {
    try {
      await this.pushTokensService.save(body.pushToken, user.id);
    } catch (err) {
      throw new InternalServerErrorException(null, { cause: err });
    }
  }
}
