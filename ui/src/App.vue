<template>
  <v-app>
    <v-app-bar
      :elevation="0"
      class="glass-app-bar position-relative"
      :class="{ 'glass-app-bar--scrolled': scrolled }"
      height="100"
    >
      <div class="app-bar-logo position-absolute w-100 d-flex align-center">
        <div class="app-bar-logo__link">
          <AppLogo />
        </div>
      </div>

      <v-spacer />

      <template #append>
        <AppConfig />
        <DarkMode />
      </template>
    </v-app-bar>
    <v-main>
      <v-container class="pt-1 pb-4">
        <h1 class="d-sr-only">Kubeseal WebGui</h1>
        <Secrets />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import Secrets from './components/Secrets.vue'
import AppLogo from './components/AppLogo.vue'
import DarkMode from './components/DarkMode.vue'
import AppConfig from './components/AppConfig.vue'

// The bar only gets its shadow once content actually scrolls under it.
const scrolled = ref(false)

function updateScrolled() {
  scrolled.value = window.scrollY > 0
}

onMounted(() => {
  updateScrolled()
  window.addEventListener('scroll', updateScrolled, { passive: true })
})

onBeforeUnmount(() => window.removeEventListener('scroll', updateScrolled))
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

/* On a phone there is no room for a centred logo next to the buttons. */
@media (max-width: 599px) {
  .app-bar-logo {
    justify-content: flex-start;
  }
}

.app-bar-logo__link {
  pointer-events: auto;
}
</style>
