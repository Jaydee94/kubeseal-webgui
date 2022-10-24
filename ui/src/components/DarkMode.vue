<template>
  <v-col cols="2">
    <v-switch
      v-model="darkMode"
      label="Dark Mode"
      @change="toggleDarkMode"
    />
  </v-col>
</template>

<script>
import { useTheme } from 'vuetify'

function isDarkModeEnabled(theme) {
  let result = false;
  let isDarkModeSetToFalse = (localStorage.useDarkTheme === 'false');
  let isDarkModeSetToTrue = (localStorage.useDarkTheme === 'true');
  let isSystemDarkModeSet = window.matchMedia('(prefers-color-scheme: dark)').matches;

  if (isDarkModeSetToFalse) {
    result = false;
  }

  if (isDarkModeSetToTrue) {
    result = true;
  }

  if (isSystemDarkModeSet && !isDarkModeSetToFalse) {
    result = true;
  }
  console.log("I take ", result)
  theme.global.name.value = result ? 'dark' : 'light'
  return result;
}

export default {
  name: "DarkMode",
  setup() {
    const theme = useTheme()
    return {
      theme,
      darkMode: isDarkModeEnabled(theme)
    }
  },
  methods: {
    toggleDarkMode: function () {
      this.theme.global.name.value = this.theme.global.current.value.dark ? 'light' : 'dark'
      localStorage.useDarkTheme = this.theme.global.current.value.dark
      this.darkMode = this.theme.global.current.value.dark
      console.log("this.darkMode:", this.darkMode)
    }
  }
}
</script>

<style scoped>

</style>