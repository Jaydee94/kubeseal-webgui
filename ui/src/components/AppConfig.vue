<template>
  <v-footer class="flex-column">
    <div class="px-1 py-1 text-center">
      <span
        v-if="fetchConfigsSuccessful"
        class="config-line text-medium-emphasis"
      >
        <span
          v-for="(value, key, index) in configs"
          :key="key"
        >
          <span v-if="index !== 0" class="config-sep"> · </span>
          <span class="config-key">{{ key }}:</span> {{ value }}
        </span>
      </span>
      <span
        v-else-if="fetchConfigsSuccessful === false"
        class="text-medium-emphasis error-message"
      >
        <v-icon size="small" class="mr-1">mdi-alert-circle</v-icon>
        Could not retrieve application properties.
      </span>
      <span
        v-else
        class="text-medium-emphasis loading-message"
      >
        <v-progress-circular indeterminate size="14" width="2" class="mr-2" />
        Loading application properties.
      </span>
    </div>
  </v-footer>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useConfig } from '@/composables/useConfig'

const configs = ref({})
const errorMessage = ref("")
const fetchConfigsSuccessful = ref(null)
const { fetchAppConfig } = useConfig()

onMounted(async () => fetchConfigs())

async function fetchConfigs() {
  try {
    const result = await fetchAppConfig();
    configs.value = result.configs;
    fetchConfigsSuccessful.value = result.success;
  } catch (error) {
    errorMessage.value = error;
    fetchConfigsSuccessful.value = false;
  }
};
</script>

<style scoped>
.config-line {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  line-height: 1.6;
}

.config-key {
  font-weight: 600;
}

.config-sep {
  opacity: 0.5;
}

.error-message,
.loading-message {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
}
</style>
