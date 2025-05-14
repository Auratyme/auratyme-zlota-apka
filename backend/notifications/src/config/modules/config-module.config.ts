import { ConfigModuleOptions } from '@nestjs/config';

import { config } from '@/src/config/env';

export const configModuleConfig: ConfigModuleOptions = {
  load: [() => config],
  isGlobal: true,
};
