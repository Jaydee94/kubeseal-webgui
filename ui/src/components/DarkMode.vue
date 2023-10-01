<template>
  <v-switch
    v-model="darkMode"
    color="blue"
    label="Dark Mode"
    class="ma-4"
    @change="toggleDarkMode"
  />
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
  this.theme.global.name.value = this.darkMode.value ? 'dark' : 'light'
  localStorage.useDarkTheme = this.theme.global.current.value.dark
}
</script>

<style scoped></style>
