import { z } from 'zod'

export const addTaskToScheduleSchema = z.object({
  taskId: z.string().uuid()
})