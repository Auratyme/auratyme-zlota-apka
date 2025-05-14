import { Task, TaskFindOptions } from "@/src/types"

/**
 * 
 * @param token 
 * @returns promise
 * @todo escape token
 */
async function find(token: string, options?: TaskFindOptions): Promise<Task[]> {
  const url = new URL(`${process.env.EXPO_PUBLIC_API_URL}/api/schedules/v1/tasks`)

  url.search = new URLSearchParams({
    limit: options?.limit?.toString() || '100',
    orderBy: options?.orderBy || 'createdAt',
    page: options?.page?.toString() || '0',
    sortBy: options?.sortBy || 'desc'
  }).toString()

  const findPromise = fetch(url, {
    method: 'GET',
    headers: {
      authorization: `Bearer ${token}`,
      'content-type': 'application/json'
    }
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error('error', {
          cause: response
        })
      }

      return response.json()
    })

  return findPromise
}

export { find }