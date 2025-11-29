<template>
  <v-row>
    <v-col
      cols="12"
      md="4"
    >
      <v-textarea
        id="secretKey"
        :model-value="secret.key"
        label="Secret key"
        rows="1"
        clearable
        prepend-icon="mdi-delete"
        variant="outlined"
        class="modern-input"
        color="primary"
        :rules="rules.validSecretKey"
        @update:model-value="$emit('update:key', $event)"
        @click:prepend="$emit('remove')"
      />
    </v-col>
    <v-col
      cols="12"
      :sm="hasValue ? 11 : hasFile ? 1 : 6"
      :md="hasValue ? 7 : hasFile ? 1 : 4"
    >
      <v-textarea
        id="secretValue"
        :model-value="secret.value"
        rows="1"
        auto-grow
        clearable
        label="Secret value"
        variant="outlined"
        class="modern-input"
        color="primary"
        :disabled="hasFile"
        @update:model-value="$emit('update:value', $event)"
      />
    </v-col>
    <v-col
      cols="12"
      :sm="hasFile ? 11 : hasValue ? 1 : 6"
      :md="hasFile ? 7 : hasValue ? 1 : 4"
    >
      <v-file-input
        id="fileInput"
        :model-value="secret.file"
        show-size
        dense
        clearable
        label="Upload File"
        prepend-icon="mdi-file-upload-outline"
        variant="outlined"
        class="modern-input"
        color="primary"
        :rules="rules.fileSize"
        :error-messages="fileError"
        :disabled="hasValue"
        :multiple="false"
        @update:model-value="$emit('update:file', $event)"
        @change="$emit('file-change', $event)"
      />
    </v-col>
  </v-row>
</template>

<script setup>
defineProps({
  secret: {
    type: Object,
    required: true
  },
  hasValue: {
    type: Boolean,
    default: false
  },
  hasFile: {
    type: Boolean,
    default: false
  },
  rules: {
    type: Object,
    required: true
  },
  fileError: {
    type: String,
    default: ''
  }
})

defineEmits(['update:key', 'update:value', 'update:file', 'remove', 'file-change'])
</script>
