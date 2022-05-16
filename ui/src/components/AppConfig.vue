<template>
  <div class="app-config">
    <b-container>
      <b-row>
        <b-col>
          <small class="text-muted" v-if="fetchConfigsSuccessful">
            <span v-for="(value, key, index) in configs" :key="value">
              <span v-if="index != 0"> 🞄 </span><span>{{key}}: {{value}}</span>
            </span>
          </small>
          <small class="text-muted" v-else-if="fetchConfigsSuccessful == false">
            ⚠️ Could not retrieve application properties.
          </small>
          <small class="text-muted" v-else>
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
  mounted() {
    this.fetchConfigs();
  },
  data: function () {
    return {
      configs: {},
      errorMessage: "",
      fetchConfigsSuccessful: null,
    };
  },
};
</script>

<style scoped>
.app-config{
  margin: 8px 0;
  text-align: center;
}
</style>

