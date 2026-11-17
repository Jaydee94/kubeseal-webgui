<template>
  <v-btn
    icon
    variant="text"
    class="dark-mode-toggle"
    :aria-label="label"
    @click="darkMode = !darkMode"
  >
    <!-- The keyed icon swaps with a short rotate/fade instead of jumping. -->
    <transition name="theme-icon" mode="out-in">
      <v-icon :key="icon" :icon="icon" />
    </transition>
    <v-tooltip activator="parent" location="bottom">{{ label }}</v-tooltip>
  </v-btn>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
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

// The button names the action, so it reads the same to everyone.
const label = computed(() => (darkMode.value ? 'Switch to light theme' : 'Switch to dark theme'))
const icon = computed(() => (darkMode.value ? 'mdi-weather-night' : 'mdi-white-balance-sunny'))

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
.theme-icon-enter-active,
.theme-icon-leave-active {
  transition:
    transform var(--transition-base, 0.3s ease),
    opacity var(--transition-base, 0.3s ease);
}

.theme-icon-enter-from {
  transform: rotate(-90deg) scale(0.6);
  opacity: 0;
}

.theme-icon-leave-to {
  transform: rotate(90deg) scale(0.6);
  opacity: 0;
}

/* No spinning for people who asked for less motion; the icon just swaps. */
@media (prefers-reduced-motion: reduce) {
  .theme-icon-enter-active,
  .theme-icon-leave-active {
    transition: none;
  }
}
</style>
