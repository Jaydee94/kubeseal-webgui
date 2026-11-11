<template>
  <v-switch v-model="darkMode" color="primary" class="ma-4 dark-mode-switch" hide-details>
    <template #label>
      <div class="d-flex align-center">
        <v-icon
          :icon="darkMode ? 'mdi-weather-night' : 'mdi-white-balance-sunny'"
          class="dark-mode-icon mr-2"
        />
        <span class="switch-label">{{ darkMode ? 'Dark' : 'Light' }}</span>
      </div>
    </template>
  </v-switch>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useTheme } from 'vuetify'
import { createLogger } from '@/utils/logger'

const log = createLogger('DarkMode')
const STORAGE_KEY = 'useDarkTheme'

// localStorage can be unavailable (privacy mode, blocked site data).
function readStoredPreference() {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch (error) {
    log.warn('Could not read the theme preference from localStorage:', error)
    return null
  }
}

function storePreference(dark) {
  try {
    localStorage.setItem(STORAGE_KEY, String(dark))
  } catch (error) {
    log.warn('Could not store the theme preference in localStorage:', error)
  }
}

/** The stored choice of the user, otherwise the preference of the system. */
function readPreferredDark() {
  const stored = readStoredPreference()
  if (stored) {
    return stored === 'true'
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

const theme = useTheme()
const darkMode = ref(readPreferredDark())

function applyTheme(dark) {
  theme.change(dark ? 'dark' : 'light')
}

applyTheme(darkMode.value)

// Only an explicit choice is stored; until then the system preference decides.
watch(darkMode, (dark) => {
  applyTheme(dark)
  storePreference(dark)
})
</script>

<style scoped>
.dark-mode-switch {
  transition: all var(--transition-base, 0.3s ease);
}

.switch-label {
  font-weight: 500;
  transition: all var(--transition-base, 0.3s ease);
}

.dark-mode-icon {
  transition: all var(--transition-base, 0.3s ease);
}

.dark-mode-switch:hover .dark-mode-icon {
  transform: rotate(20deg);
}
</style>
