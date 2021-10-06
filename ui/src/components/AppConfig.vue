<template>
  <div class="appconfig-component">
    <br>
    <b-row>
      <b-col>
        <b-button v-b-toggle.collapse-1 variant="outline-info">Show App Information</b-button>
        <b-collapse id="collapse-1" class="mt-2">
          <b-card>
            <div v-for="(value, key) in configs" :key="value">
              {{ key }}: {{ value }}
            </div>
          </b-card>
        </b-collapse>
      </b-col>
    </b-row>
  </div>
</template>

<script>

export default {
  name: "AppConfig",
  methods: {
    fetchConfigs: async function () {
      try {

        let response_config = await fetch("/config.json");
        let data_config = await response_config.json();
        let kubeseal_webgui_ui_version = data_config["kubeseal_webgui_ui_version"];
        let kubeseal_webgui_api_version = data_config["kubeseal_webgui_api_version"];

        let response = await fetch("/config.json");
        let data = await response.json();
        let apiUrl = data["api_url"];

        response = await fetch(`${apiUrl}/config`);

        let configs = await response.json();
        this.configs = JSON.parse(configs);
        this.configs.kubeseal_webgui_ui_version = kubeseal_webgui_ui_version;
        this.configs.kubeseal_webgui_api_version = kubeseal_webgui_api_version;
      } catch (error) {
        this.errorMessage = error;
      }
    },
  },
  beforeMount() {
    this.fetchConfigs();
  },
  data: function () {
    return {
      configs: {},
    };
  },
};
</script>

