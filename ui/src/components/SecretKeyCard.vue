<template>
  <v-card
    class="modern-card secret-key-card"
    elevation="1"
    variant="outlined"
  >
    <v-card-title class="d-flex align-center px-4 py-3">
      <v-icon size="small" class="mr-2" color="primary">mdi-key-variant</v-icon>
      <span class="text-subtitle-1 font-weight-medium">{{ secretKey }}</span>
    </v-card-title>
    <template #text>
      <pre class="overflow-auto result-code"><code class="overflow-auto">{{ secretValue }}</code></pre>
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
        <v-tooltip activator="parent" location="bottom">{{ isCopied ? 'Copied!' : 'Copy value' }}</v-tooltip>
      </v-btn>
    </template>
  </v-card>
</template>

<script setup>
defineProps({
  secretKey: {
    type: String,
    required: true
  },
  secretValue: {
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
</script>
