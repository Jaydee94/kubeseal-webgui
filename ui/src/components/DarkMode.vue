<template>
  <b-form-checkbox
    v-model="useDarkTheme"
    switch
  >
    <span class="align-bottom">Dark Mode ({{ useDarkTheme }}) </span>
  </b-form-checkbox>
</template>

<script>
export default {
  name: "DarkMode",
  data() {
    return {
      useDarkTheme: '',
    }
  },
  watch: {
    useDarkTheme: function () {
      if (this.useDarkTheme) {
        document.documentElement.classList.add("dark")
        localStorage.useDarkTheme = true
      } else {
        document.documentElement.classList.remove("dark")
        localStorage.useDarkTheme = false
      }
    }
  },
  mounted: function() {
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