<template>
  <div>
    <v-divider class="my-6" />

    <div class="d-flex justify-space-between align-center mb-3">
      <div class="d-flex align-center">
        <v-card-subtitle class="text-subtitle-2 px-0 mr-2">Secret Key-Value Pairs</v-card-subtitle>
        <v-tooltip location="bottom" max-width="300" open-on-click>
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              icon="mdi-information-outline"
              size="small"
              color="medium-emphasis"
            />
          </template>
          <span
            >Specify sensitive value and corresponding key of the secret.<br /><i
              >The key must be of type: DNS Subdomain</i
            ></span
          >
        </v-tooltip>
      </div>
      <div class="d-flex align-center">
        <slot name="header-actions" />
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
    </div>

    <SecretInput
      v-for="(entry, index) in entries"
      :key="entry.id"
      :entry="entry"
      :index="index"
      :rules="rules"
      @update:key="$emit('update-entry', entry.id, { key: $event })"
      @update:value="$emit('update-entry', entry.id, { value: $event })"
      @update:file="$emit('select-file', entry.id, $event)"
      @remove="$emit('remove-entry', entry.id)"
    />

    <v-row>
      <v-col>
        <v-btn
          block
          variant="outlined"
          style="border-style: dashed; border-width: 2px; opacity: 0.8"
          prepend-icon="mdi-plus"
          color="primary"
          class="mb-4"
          @click="$emit('add-entry')"
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
  entries: {
    type: Array,
    required: true
  },
  rules: {
    type: Object,
    required: true
  }
})

defineEmits(['update-entry', 'select-file', 'add-entry', 'remove-entry', 'remove-all'])
</script>
