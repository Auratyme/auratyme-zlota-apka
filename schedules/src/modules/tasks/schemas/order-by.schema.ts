import { z } from 'zod';

export const orderByTasksSchema = z.enum([
  'createdAt',
  'dueTo',
  'updatedAt',
  'name',
  'status',
  'repeat',
]);
