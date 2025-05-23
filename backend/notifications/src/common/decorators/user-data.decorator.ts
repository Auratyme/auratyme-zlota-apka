import { ExecutionContext, createParamDecorator } from '@nestjs/common';

import { Request } from 'express';

export const UserData = createParamDecorator(
  (data: unknown, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest<Request>();

    return request.auth.user;
  },
);
