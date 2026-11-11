<template>
  <v-row>
    <v-col cols="12" md="4">
      <v-textarea
        :id="`secretKey-${index}`"
        :model-value="entry.key"
        label="Secret key"
        rows="1"
        clearable
        prepend-icon="mdi-delete"
        variant="outlined"
        class="modern-input"
        color="primary"
        :rules="rules.validSecretKey"
        @update:model-value="$emit('update:key', $event ?? '')"
        @click:prepend="$emit('remove')"
      />
    </v-col>
    <v-col cols="12" :sm="hasValue ? 11 : hasFile ? 1 : 6" :md="hasValue ? 7 : hasFile ? 1 : 4">
      <v-textarea
        :id="`secretValue-${index}`"
        :model-value="entry.value"
        rows="1"
        auto-grow
        clearable
        label="Secret value"
        variant="outlined"
        class="modern-input"
        color="primary"
        :disabled="hasFile"
        @update:model-value="$emit('update:value', $event ?? '')"
      />
    </v-col>
    <v-col cols="12" :sm="hasFile ? 11 : hasValue ? 1 : 6" :md="hasFile ? 7 : hasValue ? 1 : 4">
      <v-file-input
        :id="`fileInput-${index}`"
        :model-value="entry.file"
        show-size
        clearable
        label="Upload File"
        prepend-icon="mdi-file-upload-outline"
        variant="outlined"
        class="modern-input"
        color="primary"
        :rules="rules.fileSize"
        :error-messages="entry.fileError"
        :disabled="hasValue"
        :multiple="false"
        @update:model-value="$emit('update:file', $event ?? null)"
      />
    </v-col>
  </v-row>
</template>

<script setup>
import { computed } from 'vue'
import { entryHasFile, entryHasValue } from '@/utils/secretEntry'

const props = defineProps({
  entry: {
    type: Object,
    required: true
  },
  // Position in the list, only used to give the inputs unique ids.
  index: {
    type: Number,
    required: true
  },
  rules: {
    type: Object,
    required: true
  }
})

defineEmits(['update:key', 'update:value', 'update:file', 'remove'])

const hasValue = computed(() => entryHasValue(props.entry))
const hasFile = computed(() => entryHasFile(props.entry))
</script>
