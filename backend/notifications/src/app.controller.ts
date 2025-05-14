import { Controller, Get, HttpCode, HttpStatus } from '@nestjs/common';

import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get('/healthcheck')
  @HttpCode(HttpStatus.NO_CONTENT)
  healtcheck() {}
}
