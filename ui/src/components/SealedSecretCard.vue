<template>
  <v-card
    class="ma-1 modern-card result-card"
    elevation="1"
    variant="outlined"
  >
    <v-card-title class="d-flex align-center justify-space-between px-4 py-3">
      <div class="d-flex align-center">
        <v-icon class="mr-2" color="success" size="small">mdi-check-circle</v-icon>
        <span class="text-h6 font-weight-medium">Generated Sealed Secret</span>
      </div>
    </v-card-title>
    <template #text>
      <pre class="overflow-auto result-code"><code
        id="sealed-secret-result"
        ref="sealedSecretRef"
        class="overflow-auto"
      >apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: {{ secretName ? secretName : "# no secret name given" }}
  namespace: {{ namespaceName ? namespaceName : "# no namespace name given" }}
  annotations: {{ sealedSecretsAnnotations }}
spec:
  encryptedData: {{ renderedSecrets }}</code></pre>
    </template>
    <template #actions>
      <v-btn
        v-if="clipboardAvailable"
        :variant="isCopied ? 'flat' : 'text'"
        :color="isCopied ? 'success' : 'primary'"
        :icon="isCopied ? 'mdi-check' : 'mdi-content-copy'"
        size="small"
        class="copy-btn"
        @click="$emit('copy')"
      >
        <v-icon>{{ isCopied ? 'mdi-check' : 'mdi-content-copy' }}</v-icon>
        <v-tooltip activator="parent" location="bottom">{{ isCopied ? 'Copied!' : 'Copy to clipboard' }}</v-tooltip>
      </v-btn>
    </template>
  </v-card>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  secretName: {
    type: String,
    default: ''
  },
  namespaceName: {
    type: String,
    default: ''
  },
  sealedSecretsAnnotations: {
    type: String,
    required: true
  },
  renderedSecrets: {
    type: String,
    required: true
  },
  isCopied: {
    type: Boolean,
    default: false
  },
  clipboardAvailable: {
    type: Boolean,
    default: true
  }
})

defineEmits(['copy'])

const sealedSecretRef = ref(null)

// Expose ref for parent component to access
defineExpose({ sealedSecretRef })
</script>
