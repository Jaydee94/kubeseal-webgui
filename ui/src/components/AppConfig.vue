<template>
  <div class="container-fluid text-center p-3 fixed-bottom" v-if="fetchConfigsSuccessful">
    <b-button v-b-toggle.collapse-1 variant="outline-info" v-if="fetchConfigsSuccessful">Show Detailed App Information</b-button>
    <b-collapse id="collapse-1" class="mt-2">
      <div v-for="(value, key) in configs" :key="value">
          {{ key }}: {{ value }}
      </div>
    </b-collapse>
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
        }
        let configs = await response.json();
        this.configs = JSON.parse(configs);
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

