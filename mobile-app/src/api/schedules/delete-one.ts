
/**
 * 
 * @param id 
 * @param token 
 * @returns promise
 * @todo escape token
 */
function deleteOne(id: string, token: string): Promise<null> {
  const deleteOnePromise = fetch(`${process.env.EXPO_PUBLIC_API_URL}/api/schedules/v1/schedules/${id}`, {
    method: 'DELETE',
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

      return null
    })

  return deleteOnePromise
}

export { deleteOne }