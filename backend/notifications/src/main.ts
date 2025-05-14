import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { config } from './config/env';
import { ConsoleLogger, VersioningType } from '@nestjs/common';
import { json, urlencoded } from 'express';
import { HttpExceptionFilter } from './common/filters';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, {
    logger: new ConsoleLogger(),
  });

  app.enableShutdownHooks();

  app.useGlobalFilters(new HttpExceptionFilter());

  app.use(json(), urlencoded({ extended: true }));

  app.enableVersioning({
    type: VersioningType.URI,
  });

  await app.listen(config.app.port);
}
bootstrap();
