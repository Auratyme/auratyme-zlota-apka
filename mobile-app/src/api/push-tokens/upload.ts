async function upload(pushToken: string, token: string): Promise<void> {
  const createPromise = fetch(`${process.env.EXPO_PUBLIC_API_URL}/api/notifications/push-tokens`, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${token}`,
      'content-type': 'application/json'
    },
    body: JSON.stringify({
      pushToken
    })
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error('error', {
          cause: response
        })
      }
    })

  return createPromise
}

export { upload }