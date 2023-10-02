<template>
  <v-footer class="d-flex flex-column">
    <div class="px-1 py-1">
      <small
        v-if="fetchConfigsSuccessful"
        class="text-muted"
      >
        <template
          v-for="(value, key, index) in configs"
          :key="key"
        >
          <span v-if="index != 0"> ∙ </span><span>{{ key }}: {{ value }}</span>
        </template>
      </small>
      <small
        v-else-if="fetchConfigsSuccessful === false"
        class="text-muted"
      >
        ⚠️ Could not retrieve application properties.
      </small>
      <small
        v-else
        class="text-muted"
      >
        ⏳ Loading application properties.
      </small>
    </div>

    <div class="px-1 py-1">
      <small>{{ new Date().getFullYear() }} — Kubeseal-Webgui</small>
    </div>
  </v-footer>
</template>

<script setup>
import { ref, onMounted } from 'vue'
const configs = ref({})
const errorMessage = ref("")
const fetchConfigsSuccessful = ref(null)

onMounted(async () => fetchConfigs())

async function fetchConfigs() {
  try {
    let response_config = await fetch("/config.json");
    let data_config = await response_config.clone().json();
    let kubeseal_webgui_ui_version =
      data_config["kubeseal_webgui_ui_version"];
    let kubeseal_webgui_api_version =
      data_config["kubeseal_webgui_api_version"];
    let data = await response_config.clone().json();
    let apiUrl = data["api_url"];

    let response = await fetch(`${apiUrl}/config`);
    fetchConfigsSuccessful.value = (response.ok && response_config.ok)
    configs.value = await response.json();
    configs.value.kubeseal_webgui_ui_version = kubeseal_webgui_ui_version;
    configs.value.kubeseal_webgui_api_version = kubeseal_webgui_api_version;
  } catch (error) {
    errorMessage.value = error;
  }
};
</script>

<style scoped>
.app-config {
  margin: 8px 0;
  text-align: center;
}
</style>
