import { afterEach, describe, expect, it, vi } from 'vitest'
import { useFavoriteNamespaces } from '@/composables/useFavoriteNamespaces'
import { setLogLevel } from '@/utils/logger'

setLogLevel('silent')

function stubLocalStorage(initial = {}) {
  const items = new Map(Object.entries(initial))
  vi.stubGlobal('localStorage', {
    getItem: (key) => (items.has(key) ? items.get(key) : null),
    setItem: (key, value) => items.set(key, String(value))
  })
  return items
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useFavoriteNamespaces', () => {
  it('starts empty without stored favorites', () => {
    stubLocalStorage()
    expect([...useFavoriteNamespaces().favoriteNamespaces.value]).toEqual([])
  })

  it('reads the stored favorites', () => {
    stubLocalStorage({ favoriteNamespaces: '["team-a","team-b"]' })
    expect([...useFavoriteNamespaces().favoriteNamespaces.value]).toEqual(['team-a', 'team-b'])
  })

  it('toggles a favorite and stores the result', () => {
    const items = stubLocalStorage({ favoriteNamespaces: '["team-a"]' })
    const { favoriteNamespaces, toggleFavorite } = useFavoriteNamespaces()

    toggleFavorite('team-b')
    expect(favoriteNamespaces.value.has('team-b')).toBe(true)
    expect(items.get('favoriteNamespaces')).toBe('["team-a","team-b"]')

    toggleFavorite('team-a')
    expect(favoriteNamespaces.value.has('team-a')).toBe(false)
    expect(items.get('favoriteNamespaces')).toBe('["team-b"]')
  })

  it.each(['not json', '42', '{"a":1}', '"team-a"', 'null'])(
    'ignores unusable stored content (%s)',
    (stored) => {
      stubLocalStorage({ favoriteNamespaces: stored })
      expect([...useFavoriteNamespaces().favoriteNamespaces.value]).toEqual([])
    }
  )

  it('keeps only names from a stored list', () => {
    stubLocalStorage({ favoriteNamespaces: '["team-a",null,7,"team-b"]' })
    expect([...useFavoriteNamespaces().favoriteNamespaces.value]).toEqual(['team-a', 'team-b'])
  })

  it('works without localStorage (privacy mode)', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new Error('SecurityError')
      },
      setItem: () => {
        throw new Error('SecurityError')
      }
    })
    const { favoriteNamespaces, toggleFavorite } = useFavoriteNamespaces()

    toggleFavorite('team-a')

    expect([...favoriteNamespaces.value]).toEqual(['team-a'])
  })
})
