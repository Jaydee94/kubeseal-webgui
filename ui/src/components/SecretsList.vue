<template>
  <div>
    <v-divider class="my-6" />
    
    <div class="d-flex justify-space-between align-center mb-3">
      <div class="d-flex align-center">
        <v-card-subtitle class="text-subtitle-2 px-0 mr-2">Secret Key-Value Pairs</v-card-subtitle>
        <v-tooltip location="bottom" max-width="300" open-on-click>
          <template #activator="{ props }">
            <v-icon v-bind="props" icon="mdi-information-outline" size="small" color="medium-emphasis" />
          </template>
          <span>Specify sensitive value and corresponding key of the secret.<br><i>The key must be of type: DNS Subdomain</i></span>
        </v-tooltip>
      </div>
      <v-btn
        prepend-icon="mdi-delete-sweep"
        variant="text"
        color="error"
        size="small"
        class="text-caption"
        @click="$emit('remove-all')"
      >
        Remove All
      </v-btn>
    </div>

    <SecretInput
      v-for="(secret, counter) in secrets"
      :key="counter"
      :secret="secret"
      :has-value="hasValue[counter]"
      :has-file="hasFile[counter]"
      :rules="rules"
      :file-error="fileErrors[counter]"
      @update:key="updateSecret(counter, 'key', $event)"
      @update:value="updateSecret(counter, 'value', $event)"
      @update:file="updateSecret(counter, 'file', $event)"
      @remove="$emit('remove-secret', counter)"
      @file-change="$emit('file-change', secret.file, counter)"
    />

    <v-row>
      <v-col>
        <v-btn
          block
          variant="outlined"
          style="border-style: dashed; border-width: 2px; opacity: 0.8;"
          prepend-icon="mdi-plus"
          color="primary"
          class="mb-4"
          @click="$emit('add-secret')"
        >
          Add key-value pair
        </v-btn>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import SecretInput from './SecretInput.vue'

defineProps({
  secrets: {
    type: Array,
    required: true
  },
  hasValue: {
    type: Array,
    required: true
  },
  hasFile: {
    type: Array,
    required: true
  },
  rules: {
    type: Object,
    required: true
  },
  fileErrors: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['update:secrets', 'add-secret', 'remove-secret', 'remove-all', 'file-change'])

function updateSecret(index, field, value) {
  emit('update:secrets', { index, field, value })
}
</script>
