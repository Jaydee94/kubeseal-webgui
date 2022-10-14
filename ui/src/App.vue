<template>
  <v-app>
    <header>
      <v-container>
        <nav class="navbar navbar-light">
          <v-row>
            <Logo />
            <DarkMode />
          </v-row>
        </nav>
      </v-container>
    </header>
    <v-main>
      <v-container>
        <Secrets />
      </v-container>
    </v-main>
    <v-footer
      inset
      app
      class="py-12"
      width="auto"
    >
      <AppConfig />
    </v-footer>
  </v-app>
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

</style>
