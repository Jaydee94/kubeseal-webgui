import { Base64 } from 'js-base64'
import { mockNamespacesResolver } from '@/utils/mockData'
import { requestJson } from '@/utils/http'

export function useSecrets() {
  async function fetchNamespaces(config) {
    if (import.meta.env.VITE_MOCK_NAMESPACES) {
      return mockNamespacesResolver(10)
    } else {
      return await requestJson(`${config.api_url}/namespaces`)
    }
  }

  async function fetchSealedSecrets(config, namespaceName) {
    return await requestJson(
      `${config.api_url}/sealed-secrets/${encodeURIComponent(namespaceName)}`
    )
  }

  function readFileAsync(file) {
    return new Promise((resolve, reject) => {
      let reader = new FileReader()
      reader.onload = () => {
        resolve(reader.result)
      }
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  async function fetchEncodedSecrets(config, { secretName, namespaceName, scope, secrets }) {
    const requestObject = {
      secret: secretName,
      namespace: namespaceName,
      scope: scope,
      secrets: await Promise.all(
        secrets.map(async (element) => {
          if (element.value) {
            return {
              key: element.key,
              value: Base64.encode(element.value)
            }
          } else {
            let fileContent = await readFileAsync(element.file)
            // we get a dataurl, so split the header from the data and use data, only
            fileContent = fileContent.split(',')[1]
            return {
              key: element.key,
              file: fileContent
            }
          }
        })
      )
    }

    const requestBody = JSON.stringify(requestObject, null, '\t')

    // requestJson logs method, URL and status only -- never this body, which
    // contains the cleartext secrets.
    return await requestJson(`${config.api_url}/secrets`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: requestBody
    })
  }

  return {
    fetchNamespaces,
    fetchSealedSecrets,
    fetchEncodedSecrets
  }
}
