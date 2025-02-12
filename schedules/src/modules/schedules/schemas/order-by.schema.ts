import { z } from 'zod';

export const schedulesOrderBySchema = z.enum([
  'createdAt',
  'updatedAt',
  'name',
]);
