<template>
  <div>
    <v-row justify="end">
      <v-col
        cols="12"
        md="2"
      >
        <v-select
          :model-value="scope"
          :items="scopes"
          :select-size="1"
          :plain="true"
          label="Scope"
          variant="outlined"
          class="modern-input"
          color="primary"
          @update:model-value="$emit('update:scope', $event)"
        >
          <template #append-inner>
            <v-tooltip location="bottom" max-width="300" open-on-click>
              <template #activator="{ props: activatorProps }">
                <v-icon v-bind="activatorProps" icon="mdi-information-outline" size="small" color="medium-emphasis" class="ml-2" />
              </template>
              <span>Specify scope of the secret.<br><i>Scopes for sealed secrets</i></span>
            </v-tooltip>
          </template>
        </v-select>
      </v-col>
    </v-row>
    <v-row>
      <v-col
        cols="12"
        sm="6"
        md="6"
      >
        <v-autocomplete
          id="namespaceSelection"
          :model-value="namespaceName"
          :items="sortedNamespaces"
          label="Namespace name"
          variant="outlined"
          class="modern-input"
          color="primary"
          :disabled="['strict', 'namespace-wide'].indexOf(scope) === -1"
          @update:model-value="$emit('update:namespaceName', $event)"
        >
          <template #item="{ props: itemProps, item }">
            <v-list-item
              v-bind="itemProps"
              :value="item"
              class="transition-fast"
            >
              <template #prepend>
                <v-icon
                  small
                  color="warning"
                  class="transition-fast"
                  @click.stop="$emit('toggle-favorite', item.value)"
                >
                  {{ favoriteNamespaces.has(item.value) ? 'mdi-heart' : 'mdi-heart-outline' }}
                </v-icon>
              </template>
            </v-list-item>
            <v-divider v-if="item.value === lastFavoriteNamespace" :thickness="2" class="my-2"></v-divider>
          </template>
          <template #append-inner>
            <v-tooltip location="bottom" max-width="300" open-on-click>
              <template #activator="{ props: activatorProps }">
                <v-icon v-bind="activatorProps" icon="mdi-information-outline" size="small" color="medium-emphasis" class="ml-2" />
              </template>
              Select the target namespace where the sealed secret will be deployed.
            </v-tooltip>
          </template>
        </v-autocomplete>
      </v-col>
      <v-col
        cols="12"
        sm="6"
        md="6"
      >
        <v-text-field
          id="secretName"
          :model-value="secretName"
          label="Secret name"
          trim
          clearable
          variant="outlined"
          class="modern-input"
          color="primary"
          :rules="rules.validDnsSubdomain"
          :error-messages="secretNameError"
          :disabled="['strict'].indexOf(scope) === -1"
          @update:model-value="$emit('update:secretName', $event)"
        >
          <template #append-inner>
            <v-tooltip location="bottom" max-width="300" open-on-click>
              <template #activator="{ props: activatorProps }">
                <v-icon v-bind="activatorProps" icon="mdi-information-outline" size="small" color="medium-emphasis" class="ml-2" />
              </template>
              <span>Specify name of the secret.<br><i>The secret name must be of type: DNS Subdomain</i></span>
            </v-tooltip>
          </template>
        </v-text-field>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  namespaceName: {
    type: String,
    default: ''
  },
  secretName: {
    type: String,
    default: ''
  },
  scope: {
    type: String,
    required: true
  },
  namespaces: {
    type: Array,
    required: true
  },
  scopes: {
    type: Array,
    required: true
  },
  rules: {
    type: Object,
    required: true
  },
  secretNameError: {
    type: String,
    default: ''
  },
  favoriteNamespaces: {
    type: Set,
    required: true
  }
})

defineEmits(['update:namespaceName', 'update:secretName', 'update:scope', 'toggle-favorite'])

// Sort namespaces with favorites first
const sortedNamespaces = computed(() => {
  const favorites = props.namespaces.filter(ns => props.favoriteNamespaces.has(ns))
  const others = props.namespaces.filter(ns => !props.favoriteNamespaces.has(ns))
  return [...favorites, ...others]
})

const lastFavoriteNamespace = computed(() => {
  const favorites = props.namespaces.filter(ns => props.favoriteNamespaces.has(ns))
  return favorites.length > 0 ? favorites[favorites.length - 1] : null
})
</script>
