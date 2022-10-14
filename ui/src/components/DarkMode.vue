<template>
  <v-col cols="2">
    <v-switch
      label="Dark Mode"
      @click="toggleTheme"
    />
  </v-col>
</template>

<script>
import { useTheme } from 'vuetify'


export default {
  name: "DarkMode",
  setup() {
    const theme = useTheme()
    return {
      theme,
      toggleTheme: () => {
        localStorage.useDarkTheme = theme.global.current.value.dark
        theme.global.name.value = theme.global.current.value.dark ? 'light' : 'dark'
      },
    }
  },
  watch: {
    useDarkTheme: function () {
      if (this.useDarkTheme) {
        theme.global.name.value = "dark"
        localStorage.useDarkTheme = true
      } else {
        theme.global.name.value = "light"
        localStorage.useDarkTheme = false
      }
    }
  },
  mounted: function () {
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

    this.useDarkTheme = result;
  }
}
</script>

<style scoped>
#toggle-dark-mode {
  margin-bottom: 0px;
}

span {
  color: orange;
}
</style>