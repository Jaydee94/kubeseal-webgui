<template>
  <div id="app">
    <header>
      <b-container>
        <nav class="navbar navbar-light">
          <div class="container-fluid">
            <Logo />
            <DarkMode />
          </div>
        </nav>
      </b-container>
    </header>
    <main>
      <b-container>
        <Secrets />
      </b-container>
    </main>
    <footer class="fixed-bottom">
      <AppConfig />
    </footer>
  </div>
</template>

<script>
import Secrets from './components/Secrets.vue'
import Logo from './components/Logo.vue'
import DarkMode from './components/DarkMode.vue'
import AppConfig from './components/AppConfig.vue'

export default {
  name: 'App',
  components: {
    Secrets,
    Logo,
    DarkMode,
    AppConfig
  }
}
</script>

<style scoped>

main {
  margin-bottom: 80px;
}

footer {
  background: #eee;
  height: 40px;
}

html.dark footer {
  background: #333;
}
</style>
