import { Injectable } from '@nestjs/common';
import { PushTokensRepository } from './push-tokens.repository';

@Injectable()
export class PushTokensService {
  constructor(private readonly pushTokensRepository: PushTokensRepository) {}

  async save(pushToken: string, userId: string): Promise<void> {
    return this.pushTokensRepository.save(pushToken, userId);
  }

  async find(userId: string): Promise<{ pushToken: string }[]> {
    return this.pushTokensRepository.find(userId);
  }

  async remove(pushToken: string, userId: string): Promise<void> {
    return this.pushTokensRepository.remove(pushToken, userId);
  }
}
