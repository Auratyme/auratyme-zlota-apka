import { Injectable } from '@nestjs/common';
import { DatabaseService } from '../database/database.service';
import { DatabaseException } from '@/src/common/exceptions';
import { pushTokensTable } from '../database/schemas';
import { and, eq, getTableColumns } from 'drizzle-orm';

@Injectable()
export class PushTokensRepository {
  constructor(private readonly database: DatabaseService) {}

  async save(pushToken: string, userId: string): Promise<void> {
    try {
      await this.database.db
        .insert(pushTokensTable)
        .values({ pushToken, userId });
    } catch (err) {
      throw new DatabaseException('failed to save push token', err, true);
    }
  }

  async find(userId: string): Promise<{ pushToken: string }[]> {
    try {
      const result = await this.database.db
        .select({
          pushToken: pushTokensTable.pushToken,
        })
        .from(pushTokensTable)
        .where(eq(pushTokensTable.userId, userId));

      return result;
    } catch (err) {
      throw new DatabaseException('failed to find push tokens', err, true);
    }
  }

  async remove(pushToken: string, userId: string): Promise<void> {
    try {
      await this.database.db
        .delete(pushTokensTable)
        .where(
          and(
            eq(pushTokensTable.pushToken, pushToken),
            eq(pushTokensTable.userId, userId),
          ),
        );
    } catch (err) {
      throw new DatabaseException('failed to delete push token', err, true);
    }
  }
}
