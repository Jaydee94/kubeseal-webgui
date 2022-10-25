<template>
  <v-switch
    v-model="state.darkMode"
    color="blue"
    label="Dark Mode"
    class="ma-4"
    @change="toggleDarkMode"
  />
</template>

<script>
import { useTheme } from 'vuetify'
import { reactive } from 'vue';

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

export default {
  name: "DarkMode",
  setup() {
    const theme = useTheme()
    const state = reactive({
      darkMode: isDarkModeEnabled(theme)
    })
    return {
      theme,
      state
    }
  },
  methods: {
    toggleDarkMode: function () {
      this.theme.global.name.value = this.state.darkMode ? 'dark' : 'light'
      localStorage.useDarkTheme = this.theme.global.current.value.dark
    }
  }
}
</script>

<style scoped>

</style>
