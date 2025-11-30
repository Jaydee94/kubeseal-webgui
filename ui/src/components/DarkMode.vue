<template>
  <v-switch
    v-model="darkMode"
    color="primary"
    class="ma-4 dark-mode-switch"
    hide-details
    @change="toggleDarkMode"
  >
    <template #label>
      <div class="d-flex align-center">
        <v-icon :icon="darkMode ? 'mdi-weather-night' : 'mdi-white-balance-sunny'" class="mr-2" />
        <span class="switch-label">{{ darkMode ? 'Dark' : 'Light' }}</span>
      </div>
    </template>
  </v-switch>
</template>

<script setup>
import { useTheme } from 'vuetify'
import { ref } from 'vue';

function isDarkModeEnabled(theme) {
  let result = false;

  if (localStorage.useDarkTheme) {
    result = localStorage.useDarkTheme === 'true'
  } else {
    let isSystemDarkModeSet = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (isSystemDarkModeSet) {
      result = true;
    }
  }
  theme.global.name.value = result ? 'dark' : 'light'
  return result;
}

const theme = useTheme()
const darkMode = ref(isDarkModeEnabled(theme))

function toggleDarkMode() {
  theme.global.name.value = darkMode.value ? 'dark' : 'light'
  localStorage.useDarkTheme = theme.global.current.value.dark
}
</script>

<style scoped>
.dark-mode-switch {
  transition: all var(--transition-base, 0.3s ease);
}

.switch-label {
  font-weight: 500;
  transition: all var(--transition-base, 0.3s ease);
}

.v-icon {
  transition: all var(--transition-base, 0.3s ease);
}

.dark-mode-switch:hover .v-icon {
  transform: rotate(20deg);
}
</style>
