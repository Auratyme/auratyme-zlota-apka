import { Task } from "@/src/types";
import { TaskCreateDto } from "@/src/types/tasks/create-dto";

/**
 * 
 * @param createDto 
 * @param token 
 * @returns promise
 * @todo escape token
 */
async function create(createDto: TaskCreateDto, token: string): Promise<Task> {
  const createPromise = fetch(`${process.env.EXPO_PUBLIC_API_URL}/api/schedules/v1/tasks`, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${token}`,
      'content-type': 'application/json'
    },
    body: JSON.stringify(createDto)
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error('error', {
          cause: response
        })
      }

      return response.json()
    })

  return createPromise
}

export { create }