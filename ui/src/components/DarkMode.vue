<template>
  <div class="darkModeTheme">
      <span class="align-bottom">Dark Mode: </span>
      <toggle-button id="toggle-dark-mode" :sync=true color="#333" v-model="useDarkTheme" />
  </div>
</template>

<script>
export default {
  name: "DarkMode",
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
  },
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