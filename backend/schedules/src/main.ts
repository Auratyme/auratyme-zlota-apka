import { NestFactory } from '@nestjs/core';
import { VersioningType } from '@nestjs/common';

import { json, urlencoded } from 'express';

import { HttpExceptionFilter } from './common/filters';

import { config } from './config/env';

import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.enableShutdownHooks();

  app.useGlobalFilters(new HttpExceptionFilter());

  app.use(
    json(),
    urlencoded({
      extended: true,
    }),
  );

  app.enableVersioning({
    type: VersioningType.URI,
  });

  await app.listen(config.app.port);
}

bootstrap();
