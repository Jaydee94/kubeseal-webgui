<template>
  <v-app>
    <v-app-bar :elevation="0" class="glass-app-bar position-relative" height="100">
      <div class="app-bar-logo position-absolute w-100 d-flex align-center">
        <div class="app-bar-logo__link">
          <AppLogo />
        </div>
      </div>

      <v-spacer />

      <template #append>
        <DarkMode />
      </template>
    </v-app-bar>
    <v-main>
      <v-container class="pt-1 pb-4">
        <Secrets />
      </v-container>
    </v-main>
    <v-footer app class="glass-app-bar py-2">
      <AppConfig />
    </v-footer>
  </v-app>
</template>

<script setup>
import Secrets from './components/Secrets.vue'
import AppLogo from './components/AppLogo.vue'
import DarkMode from './components/DarkMode.vue'
import AppConfig from './components/AppConfig.vue'
</script>

<style scoped>
/* The logo is centred over the whole bar, whatever else the bar contains.
   Only the logo itself takes clicks, not the area around it. */
.app-bar-logo {
  left: 0;
  height: 100%;
  justify-content: center;
  pointer-events: none;
}

/* On a phone there is no room for a centred logo next to the theme switch. */
@media (max-width: 599px) {
  .app-bar-logo {
    justify-content: flex-start;
  }
}

.app-bar-logo__link {
  pointer-events: auto;
}
</style>
