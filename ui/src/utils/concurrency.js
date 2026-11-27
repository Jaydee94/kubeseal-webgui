// Running many requests without sending them all at once.

/**
 * Map `items` with the async `fn`, running at most `limit` calls at a time.
 * The results keep the order of `items`. On the first failure no further
 * call is started and the returned promise rejects with that error (calls
 * already running are left to finish).
 */
export async function mapWithLimit(items, limit, fn) {
  // With no worker nothing would run, and the result would be silently empty.
  if (!Number.isInteger(limit) || limit < 1) {
    throw new RangeError(`limit must be a positive integer, got ${limit}`)
  }
  const results = new Array(items.length)
  let next = 0
  let failed = false

  async function worker() {
    while (!failed && next < items.length) {
      const index = next++
      try {
        results[index] = await fn(items[index], index)
      } catch (error) {
        failed = true
        throw error
      }
    }
  }

  const workers = Array.from({ length: Math.min(limit, items.length) }, worker)
  await Promise.all(workers)
  return results
}
