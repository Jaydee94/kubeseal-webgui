import { requestJson } from '@/utils/http'

export function useConfig() {
  async function fetchConfig() {
    return await requestJson('/config.json')
  }

  async function fetchAppConfig() {
    const data_config = await fetchConfig()

    const kubeseal_webgui_ui_version = data_config['kubeseal_webgui_ui_version']
    const kubeseal_webgui_api_version = data_config['kubeseal_webgui_api_version']
    const apiUrl = data_config['api_url']

    const configs = await requestJson(`${apiUrl}/config`)
    configs.uiVersion = kubeseal_webgui_ui_version
    configs.apiVersion = kubeseal_webgui_api_version

    return {
      configs,
      success: true
    }
  }

  return {
    fetchConfig,
    fetchAppConfig
  }
}
