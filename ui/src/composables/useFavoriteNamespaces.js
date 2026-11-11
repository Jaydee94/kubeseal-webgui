import { ref } from 'vue'
import { createLogger } from '@/utils/logger'

const log = createLogger('favorites')
const STORAGE_KEY = 'favoriteNamespaces'

// localStorage can be unavailable (privacy mode, blocked site data) and its
// content can be anything, so both directions are guarded.
function readStoredFavorites() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return new Set(stored === null ? [] : JSON.parse(stored))
  } catch (error) {
    log.warn('Ignoring unreadable favorite namespaces in localStorage:', error)
    return new Set()
  }
}

function storeFavorites(favorites) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...favorites]))
  } catch (error) {
    log.warn('Could not store favorite namespaces in localStorage:', error)
  }
}

/** The namespaces a user marked as favorites, remembered in this browser. */
export function useFavoriteNamespaces() {
  const favoriteNamespaces = ref(readStoredFavorites())

  function toggleFavorite(namespace) {
    if (favoriteNamespaces.value.has(namespace)) {
      favoriteNamespaces.value.delete(namespace)
    } else {
      favoriteNamespaces.value.add(namespace)
    }
    storeFavorites(favoriteNamespaces.value)
  }

  return { favoriteNamespaces, toggleFavorite }
}
