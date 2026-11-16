<template>
  <v-menu :close-on-content-click="false" location="bottom end" offset="8">
    <template #activator="{ props: menuProps }">
      <v-btn v-bind="menuProps" icon variant="text" class="about-button" aria-label="About">
        <v-icon icon="mdi-information-outline" />
        <v-tooltip activator="parent" location="bottom">About</v-tooltip>
      </v-btn>
    </template>

    <v-card class="about-card" min-width="260" max-width="320">
      <v-card-title class="text-h6">Kubeseal WebGui</v-card-title>
      <v-card-text>
        <dl v-if="fetchConfigsSuccessful" class="about-versions">
          <template v-for="(value, key) in configs" :key="key">
            <dt>{{ labels[key] ?? key }}</dt>
            <dd>{{ value }}</dd>
          </template>
        </dl>
        <small v-else-if="fetchConfigsSuccessful === false" class="status-message">
          <v-icon class="mr-1">mdi-alert-circle</v-icon>
          Could not retrieve application properties.
        </small>
        <small v-else class="status-message">
          <v-icon class="mr-1 rotating">mdi-loading</v-icon>
          Loading application properties.
        </small>
      </v-card-text>
      <v-divider />
      <v-card-actions>
        <v-btn
          :href="REPOSITORY_URL"
          target="_blank"
          rel="noopener noreferrer"
          variant="text"
          color="primary"
          prepend-icon="mdi-github"
          append-icon="mdi-open-in-new"
        >
          GitHub
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchApiConfig } from '@/api'
import { loadConfig } from '@/config'
import { createLogger } from '@/utils/logger'

const log = createLogger('AppConfig')

const REPOSITORY_URL = 'https://github.com/Jaydee94/kubeseal-webgui'

// Readable names for the properties; an unknown one is shown under its own key.
const labels = {
  kubesealVersion: 'Kubeseal',
  uiVersion: 'UI',
  apiVersion: 'API'
}

// The properties shown in the list, in this order.
const configs = ref({})
// null while loading, afterwards whether loading worked.
const fetchConfigsSuccessful = ref(null)

// Loaded when the page loads, not when the popover opens, so it is ready by
// the time someone looks and config.json is still requested only once.
onMounted(async () => {
  try {
    const { uiVersion, apiVersion } = await loadConfig()
    configs.value = { ...(await fetchApiConfig()), uiVersion, apiVersion }
    fetchConfigsSuccessful.value = true
  } catch (error) {
    log.error('Could not retrieve application properties:', error)
    fetchConfigsSuccessful.value = false
  }
})
</script>

<style scoped>
.about-versions {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.5rem 1.5rem;
  margin: 0;
}

.about-versions dt {
  color: rgb(var(--v-theme-on-surface-variant));
}

.about-versions dd {
  margin: 0;
  font-weight: 500;
  overflow-wrap: anywhere;
}

.status-message {
  display: flex;
  align-items: center;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.rotating {
  animation: rotate 1s linear infinite;
}

/* A spinner that never moves still says "loading" through its text. */
@media (prefers-reduced-motion: reduce) {
  .rotating {
    animation: none;
  }
}
</style>
