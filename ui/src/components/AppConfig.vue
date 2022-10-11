<template>
  <div class="app-config">
    <b-container>
      <b-row>
        <b-col>
          <small
            v-if="fetchConfigsSuccessful"
            class="text-muted"
          >
            <span
              v-for="(value, key, index) in configs"
              :key="key"
            >
              <span v-if="index != 0"> 🞄 </span><span>{{ key }}: {{ value }}</span>
            </span>
          </small>
          <small
            v-else-if="fetchConfigsSuccessful == false"
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
        </b-col>
      </b-row>
    </b-container>
  </div>
</template>

<script>

export default {
  name: "AppConfig",
  data: function () {
    return {
      configs: {},
      errorMessage: "",
      fetchConfigsSuccessful: null,
    };
  },
  mounted() {
    this.fetchConfigs();
  },
  methods: {
    fetchConfigs: async function () {
      try {
        let response_config = await fetch("/config.json");
        let data_config = await response_config.clone().json();
        let kubeseal_webgui_ui_version = data_config["kubeseal_webgui_ui_version"];
        let kubeseal_webgui_api_version = data_config["kubeseal_webgui_api_version"];
        let data = await response_config.clone().json();
        let apiUrl = data["api_url"];

        let response = await fetch(`${apiUrl}/config`);
        this.code2 = response.ok;
        if (response.ok && response_config.ok) {
          this.fetchConfigsSuccessful = true;
        } else {
          this.fetchConfigsSuccessful = false
        }
        let configs = await response.json();
        this.configs = configs;
        this.configs.kubeseal_webgui_ui_version = kubeseal_webgui_ui_version;
        this.configs.kubeseal_webgui_api_version = kubeseal_webgui_api_version;
      } catch (error) {
        this.errorMessage = error;
      }
    },
  },
};
</script>

<style scoped>
.app-config{
  margin: 8px 0;
  text-align: center;
}
</style>

