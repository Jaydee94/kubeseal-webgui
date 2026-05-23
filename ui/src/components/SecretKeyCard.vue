<template>
  <v-card
    class="modern-card secret-key-card"
    :elevation="0"
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
        size="small"
        class="copy-btn"
        :aria-label="isCopied ? 'Copied to clipboard' : 'Copy value to clipboard'"
        @click="$emit('copy')"
      >
        <v-icon class="mr-1">{{ isCopied ? 'mdi-check' : 'mdi-content-copy-outline' }}</v-icon>
        {{ isCopied ? 'Copied!' : 'Copy value' }}
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
