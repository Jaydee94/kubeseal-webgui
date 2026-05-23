<template>
  <v-card
    class="ma-1 modern-card result-card"
    :elevation="0"
    variant="outlined"
  >
    <v-card-title class="d-flex align-center justify-space-between px-4 py-3">
      <div class="d-flex align-center">
        <v-icon class="mr-2" color="success" size="small">mdi-check-circle</v-icon>
        <span class="text-h6 font-weight-medium">Generated Sealed Secret</span>
      </div>
    </v-card-title>
    <template #text>
      <!-- eslint-disable vue/no-v-html -- highlight.js HTML-escapes the input, so this is safe -->
      <pre class="overflow-auto result-code sealed-yaml"><code
        id="sealed-secret-result"
        ref="sealedSecretRef"
        class="hljs overflow-auto"
        v-html="highlightedYaml"
      ></code></pre>
      <!-- eslint-enable vue/no-v-html -->
    </template>
    <template #actions>
      <v-btn
        v-if="clipboardAvailable"
        :variant="isCopied ? 'flat' : 'text'"
        :color="isCopied ? 'success' : 'primary'"
        size="small"
        class="copy-btn"
        :aria-label="isCopied ? 'Copied to clipboard' : 'Copy sealed secret to clipboard'"
        @click="$emit('copy')"
      >
        <v-icon class="mr-1">{{ isCopied ? 'mdi-check' : 'mdi-content-copy-outline' }}</v-icon>
        {{ isCopied ? 'Copied!' : 'Copy' }}
      </v-btn>
    </template>
  </v-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import hljs from 'highlight.js/lib/core'
import yaml from 'highlight.js/lib/languages/yaml'

hljs.registerLanguage('yaml', yaml)

const props = defineProps({
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

const sealedSecretYaml = computed(() => {
  const name = props.secretName ? props.secretName : '# no secret name given'
  const namespace = props.namespaceName ? props.namespaceName : '# no namespace name given'
  return `apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: ${name}
  namespace: ${namespace}
  annotations: ${props.sealedSecretsAnnotations}
spec:
  encryptedData: ${props.renderedSecrets}`
})

const highlightedYaml = computed(() =>
  hljs.highlight(sealedSecretYaml.value, { language: 'yaml' }).value
)

const sealedSecretRef = ref(null)

// Expose ref for parent component to access (used for clipboard copy)
defineExpose({ sealedSecretRef })
</script>

<!-- Non-scoped: highlight.js renders global token classes inside v-html -->
<style>
.sealed-yaml .hljs-attr,
.sealed-yaml .hljs-attribute {
  color: rgb(var(--v-theme-primary));
  font-weight: 600;
}

.sealed-yaml .hljs-string {
  color: rgb(var(--v-theme-success));
}

.sealed-yaml .hljs-number,
.sealed-yaml .hljs-literal,
.sealed-yaml .hljs-bool {
  color: rgb(var(--v-theme-secondary));
}

.sealed-yaml .hljs-bullet,
.sealed-yaml .hljs-meta,
.sealed-yaml .hljs-tag {
  color: rgb(var(--v-theme-info));
}

.sealed-yaml .hljs-comment {
  color: rgb(var(--v-theme-on-surface-variant));
  font-style: italic;
}
</style>
