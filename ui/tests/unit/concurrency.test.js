import { describe, expect, it } from 'vitest'
import { mapWithLimit } from '@/utils/concurrency'

const tick = () => new Promise((resolve) => setTimeout(resolve, 1))

describe('mapWithLimit', () => {
  it('keeps the order of the items', async () => {
    // later items finish first
    const result = await mapWithLimit([3, 1, 2], 3, async (n) => {
      await new Promise((resolve) => setTimeout(resolve, n))
      return n * 10
    })
    expect(result).toEqual([30, 10, 20])
  })

  it('runs at most `limit` calls at a time', async () => {
    let running = 0
    let most = 0
    await mapWithLimit([1, 2, 3, 4, 5, 6, 7], 3, async () => {
      running++
      most = Math.max(most, running)
      await tick()
      running--
    })
    expect(most).toBe(3)
  })

  it('starts no further call after a failure', async () => {
    const started = []
    await expect(
      mapWithLimit([1, 2, 3, 4], 1, async (n) => {
        started.push(n)
        if (n === 2) throw new Error('failed for 2')
      })
    ).rejects.toThrow('failed for 2')
    expect(started).toEqual([1, 2])
  })

  it('has nothing to do for no items', async () => {
    await expect(mapWithLimit([], 4, async () => 1)).resolves.toEqual([])
  })
})
