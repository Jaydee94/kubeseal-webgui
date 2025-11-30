<template>
  <v-app>
    <v-app-bar 
      :elevation="0" 
      class="glass-app-bar position-relative"
      height="100"
    >
      <div class="position-absolute w-100 d-flex justify-center align-center" style="pointer-events: none; left: 0; height: 100%;">
        <div style="pointer-events: auto;">
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
    <v-footer
      inset
      app
      class="glass-app-bar py-2"
      width="auto"
    >
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

<style scoped></style>
