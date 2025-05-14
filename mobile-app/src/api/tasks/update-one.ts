import { TaskUpdateDto } from "@/src/types"

function updateOne(id: string, updateDto: TaskUpdateDto, token: string): Promise<null> {
  const updateOnePromise = fetch(`${process.env.EXPO_PUBLIC_API_URL}/api/schedules/v1/tasks/${id}`, {
    method: 'PATCH',
    headers: {
      authorization: `Bearer ${token}`,
      'content-type': 'application/json'
    },
    body: JSON.stringify(updateDto)
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error('error', {
          cause: response
        })
      }

      return null
    })

  return updateOnePromise
}

export { updateOne }