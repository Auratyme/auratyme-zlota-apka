export function removeTask(scheduleId: string, taskId: string, token: string): Promise<void> {
  const url = new URL(`${process.env.EXPO_PUBLIC_API_URL}/api/schedules/v1/schedules/${scheduleId}/tasks/${taskId}`)

  const removePromise = fetch(url, {
    method: 'DELETE',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${token}`
    },
  }).then((res) => {
    if (!res.ok) {
      throw new Error('error', { cause: res })
    }
  })

  return removePromise
}