<template>
  <v-app>
    <v-app-bar
      :elevation="0"
      class="glass-app-bar"
      :class="{ 'glass-app-bar--scrolled': scrolled }"
      height="64"
    >
      <!-- Same width as the content below, so logo and panels line up. -->
      <div class="app-bar__inner">
        <AppLogo />
        <!-- Which installation this is (display_name of config.json), so that
             nobody seals for the wrong cluster by mistake. -->
        <span v-if="displayName" class="env-badge" :title="`Environment: ${displayName}`">
          <span class="env-badge__dot" aria-hidden="true" />
          <span class="d-sr-only">Environment:</span>
          <span class="env-badge__name">{{ displayName }}</span>
        </span>
        <v-spacer />
        <DarkMode />
      </div>
    </v-app-bar>
    <v-main>
      <v-container class="app-content">
        <h1 class="d-sr-only">Kubeseal WebGui</h1>
        <Secrets />
      </v-container>
    </v-main>
    <AppFooter />
  </v-app>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import Secrets from './components/Secrets.vue'
import AppLogo from './components/AppLogo.vue'
import DarkMode from './components/DarkMode.vue'
import AppFooter from './components/AppFooter.vue'
import { loadConfig } from './config'

// The bar only gets its line and shadow once content actually scrolls under it.
const scrolled = ref(false)
const displayName = ref('')

function updateScrolled() {
  scrolled.value = window.scrollY > 0
}

onMounted(async () => {
  updateScrolled()
  window.addEventListener('scroll', updateScrolled, { passive: true })
  // Shares the one request for config.json; a failure is reported by the form.
  try {
    displayName.value = (await loadConfig()).displayName
  } catch {
    displayName.value = ''
  }
})

onBeforeUnmount(() => window.removeEventListener('scroll', updateScrolled))
</script>

<style scoped>
.app-bar__inner {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  /* The content column (960px) plus the container's padding. */
  max-width: calc(960px + 2 * 16px);
  margin: 0 auto;
  padding: 0 16px;
}

/* The bar's own padding would push the inner row off the content column. */
:deep(.v-toolbar__content) {
  padding: 0;
}

.app-content {
  padding-top: 24px;
  padding-bottom: 40px;
}

.env-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  height: 28px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: var(--radius-full);
  background: rgba(var(--v-theme-surface), 0.5);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
}

.env-badge__dot {
  flex: none;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgb(var(--v-theme-secondary));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-secondary), 0.18);
}

.env-badge__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 599px) {
  .app-content {
    padding-top: 16px;
  }
}
</style>
