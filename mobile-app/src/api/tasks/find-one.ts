import { Task } from "@/src/types"

/**
 * 
 * @param id 
 * @param token 
 * @returns promise
 * @todo escape token
 */
async function findOne(id: string, token: string): Promise<Task> {
  const findOnePromise = fetch(`${process.env.EXPO_PUBLIC_API_URL}/api/schedules/v1/tasks/${id}`, {
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

  return findOnePromise
}

export { findOne }