import { ConfigModuleOptions } from '@nestjs/config';

import { config } from '@app/config/env';

export const configModuleConfig: ConfigModuleOptions = {
  load: [() => config],
  isGlobal: true,
};
