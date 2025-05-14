import { Schedule } from "@/src/types"

/**
 * 
 * @param token 
 * @returns promise
 * @todo escape token
 */
function find(token: string): Promise<Schedule[]> {
  const findPromise = fetch(`${process.env.EXPO_PUBLIC_API_URL}/api/schedules/v1/schedules`, {
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