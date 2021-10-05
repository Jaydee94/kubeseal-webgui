<template>
  <div id="app">
    <b-container>
      <nav class="navbar navbar-light">
        <div class="container-fluid">
          <Logo />
          <DarkMode />
        </div>
      </nav>
      <Secrets />
    </b-container>
  </div>
</template>

<script>
import Secrets from './components/Secrets.vue'
import Logo from './components/Logo.vue'
import DarkMode from './components/DarkMode.vue'

export default {
  name: 'App',
  components: {
    Secrets,
    Logo,
    DarkMode,
  }
}
</script>