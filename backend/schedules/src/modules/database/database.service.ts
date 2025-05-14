import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { drizzle, NodePgDatabase } from 'drizzle-orm/node-postgres';

import { Pool } from 'pg';

import * as schema from './schemas';

import { DatabaseConfig } from '@app/common/types';

@Injectable({})
export class DatabaseService {
  private config: DatabaseConfig;
  private pool: Pool;
  private logger = new Logger(DatabaseService.name);

  public db: NodePgDatabase<typeof schema>;

  constructor(private configService: ConfigService) {
    this.config = this.configService.get<DatabaseConfig>('db', {
      infer: true,
    });

    const { host, name, password, port, user } = this.config;
    const connectionString = `postgresql://${user}:${password}@${host}:${port}/${name}`;

    this.pool = new Pool({ connectionString });

    this.db = drizzle({
      client: this.pool,
      logger: {
        logQuery: (query, params) => {
          this.logger.debug(
            {
              query: query,
              params: params,
            },
            'query',
          );
        },
      },
      schema: { ...schema },
    });
  }

  async init() {}

  async close() {
    await this.pool.end();
    this.logger.log('database connection closed');
  }
}
