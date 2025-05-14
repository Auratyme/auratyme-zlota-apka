import { Task, TaskFindOptions } from '@/src/types'

export function findTasks(scheduleId: string, options: TaskFindOptions, token: string): Promise<Task[]> {
  const url = new URL(`${process.env.EXPO_PUBLIC_API_URL}/api/schedules/v1/schedules/${scheduleId}/tasks`)

  url.search = new URLSearchParams({
    imit: options?.limit?.toString() || '10',
    orderBy: options?.orderBy || 'createdAt',
    page: options?.page?.toString() || '0',
    sortBy: options?.sortBy || 'desc'
  }).toString()

  const findPromise = fetch(url, {
    method: 'GET',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${token}`
    }
  }).then((res) => {
    if (!res.ok) {
      throw new Error('error', {
        cause: res
      })
    }

    return res.json()
  })

  return findPromise
}