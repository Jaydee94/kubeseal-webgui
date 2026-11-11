<template>
  <v-footer class="flex-column">
    <div class="px-1 py-1">
      <small v-if="fetchConfigsSuccessful">
        <v-chip
          v-for="(value, key) in configs"
          :key="key"
          variant="flat"
          size="small"
          class="modern-chip ma-1"
          color="primary"
        >
          <span class="chip-content">
            <strong>{{ key }}:</strong> {{ value }}
          </span>
        </v-chip>
      </small>
      <small v-else-if="fetchConfigsSuccessful === false" class="error-message">
        <v-icon class="mr-1">mdi-alert-circle</v-icon>
        Could not retrieve application properties.
      </small>
      <small v-else class="loading-message">
        <v-icon class="mr-1 rotating">mdi-loading</v-icon>
        Loading application properties.
      </small>
    </div>
  </v-footer>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchApiConfig } from '@/api'
import { loadConfig } from '@/config'
import { createLogger } from '@/utils/logger'

const log = createLogger('AppConfig')

// The properties shown as chips, in this order.
const configs = ref({})
// null while loading, afterwards whether loading worked.
const fetchConfigsSuccessful = ref(null)

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
.modern-chip {
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  transition: all var(--transition-base, 0.3s ease);
  opacity: 0.9;
}

.modern-chip:hover {
  opacity: 1;
  transform: translateY(-2px);
}

.chip-content {
  font-size: 0.75rem;
}

.error-message,
.loading-message {
  display: flex;
  align-items: center;
  justify-content: center;
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
</style>
