export function useConfig() {
  async function fetchConfig() {
    const response = await fetch("/config.json");
    if (!response.ok) {
      throw Error(`Failed to fetch config.json: ${response.statusText}`);
    }
    return await response.json();
  }

  async function fetchAppConfig() {
    const response_config = await fetch("/config.json");
    if (!response_config.ok) {
      throw Error(`Failed to fetch config.json: ${response_config.statusText}`);
    }
    const data_config = await response_config.clone().json();
    
    const kubeseal_webgui_ui_version = data_config["kubeseal_webgui_ui_version"];
    const kubeseal_webgui_api_version = data_config["kubeseal_webgui_api_version"];
    const apiUrl = data_config["api_url"];

    const response = await fetch(`${apiUrl}/config`);
    
    const configs = await response.json();
    configs.uiVersion = kubeseal_webgui_ui_version;
    configs.apiVersion = kubeseal_webgui_api_version;
    
    return {
      configs,
      success: response.ok && response_config.ok
    };
  }

  return {
    fetchConfig,
    fetchAppConfig
  };
}
