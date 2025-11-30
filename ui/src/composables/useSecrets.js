import { Base64 } from "js-base64";
import { mockNamespacesResolver } from "@/utils/mockData";

export function useSecrets() {
  async function fetchNamespaces(config) {
    if (import.meta.env.VITE_MOCK_NAMESPACES) {
      return mockNamespacesResolver(10);
    } else {
      const response = await fetch(`${config.api_url}/namespaces`);
      if (!response.ok) {
          throw new Error(`Failed to fetch namespaces: ${response.statusText}`);
      }
      return await response.json();
    }
  }

  function readFileAsync(file) {
    return new Promise((resolve, reject) => {
      let reader = new FileReader();
      reader.onload = () => {
        resolve(reader.result);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
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
              value: Base64.encode(element.value),
            };
          } else {
            let fileContent = await readFileAsync(element.file);
            // we get a dataurl, so split the header from the data and use data, only
            fileContent = fileContent.split(",")[1];
            return {
              key: element.key,
              file: fileContent,
            };
          }
        })
      ),
    };

    const requestBody = JSON.stringify(requestObject, null, "\t");

    const response = await fetch(`${config.api_url}/secrets`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: requestBody,
    });

    if (!response.ok) {
      throw Error(
        "No sealed secrets in response from backend: " +
        (await response.text())
      );
    } else {
      return await response.json();
    }
  }

  return {
    fetchNamespaces,
    fetchEncodedSecrets
  };
}
