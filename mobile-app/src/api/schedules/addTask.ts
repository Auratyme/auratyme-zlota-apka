export function addTask(scheduleId: string, taskId: string, token: string): Promise<void> {
  const url = new URL(`${process.env.EXPO_PUBLIC_API_URL}/api/schedules/v1/schedules/${scheduleId}/tasks`)

  const addPromise = fetch(url, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
      taskId: taskId
    })
  }).then((res) => {
    if (!res.ok) {
      throw new Error('error', { cause: res })
    }
  })

  return addPromise
}