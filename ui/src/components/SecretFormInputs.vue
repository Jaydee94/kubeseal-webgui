<template>
  <div>
    <v-row justify="end">
      <v-col cols="12" sm="6">
        <v-select
          :model-value="scope"
          :items="SCOPES"
          label="Scope"
          variant="outlined"
          class="modern-input"
          color="primary"
          @update:model-value="$emit('update:scope', $event)"
        >
          <template #append-inner>
            <InfoTooltip class="ml-2">
              <span>Specify scope of the secret.<br /><i>Scopes for sealed secrets</i></span>
            </InfoTooltip>
          </template>
        </v-select>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12" sm="6" md="6">
        <v-text-field
          v-if="newNamespace"
          id="namespaceSelection"
          :model-value="namespaceName"
          label="New namespace name"
          autocomplete="off"
          clearable
          variant="outlined"
          class="modern-input"
          color="primary"
          :rules="rules.validNamespace"
          :disabled="!namespaceNeeded"
          hide-details="auto"
          @update:model-value="$emit('update:namespaceName', $event ?? '')"
        >
          <template #append-inner>
            <InfoTooltip class="ml-2">
              <span
                >Name of a namespace that does not exist yet.<br /><i
                  >The secret is sealed for exactly this name, so double-check it for typos.</i
                ></span
              >
            </InfoTooltip>
          </template>
        </v-text-field>
        <v-autocomplete
          v-else
          id="namespaceSelection"
          :model-value="namespaceName"
          :items="sortedNamespaces"
          label="Namespace name"
          autocomplete="off"
          variant="outlined"
          class="modern-input"
          color="primary"
          :disabled="!namespaceNeeded"
          @update:model-value="$emit('update:namespaceName', $event)"
        >
          <!-- `item` is the namespace name (Vuetify 4 passes the raw item). -->
          <template #item="{ props: itemProps, item }">
            <v-list-item v-bind="itemProps" :value="item" class="transition-fast">
              <template #prepend>
                <v-btn
                  icon
                  variant="text"
                  color="warning"
                  size="24"
                  class="favorite-toggle transition-fast"
                  :aria-label="favoriteToggleLabel(item)"
                  :aria-pressed="favoriteNamespaces.has(item)"
                  @click.stop="toggleFavorite(item, $event)"
                  @keydown.enter.space.stop
                >
                  <v-icon
                    :icon="favoriteNamespaces.has(item) ? 'mdi-heart' : 'mdi-heart-outline'"
                  />
                </v-btn>
              </template>
            </v-list-item>
            <v-divider
              v-if="item === lastFavoriteNamespace"
              :thickness="2"
              class="my-2"
            ></v-divider>
          </template>
          <template #append-inner>
            <InfoTooltip class="ml-2">
              Select the target namespace where the sealed secret will be deployed.
            </InfoTooltip>
          </template>
        </v-autocomplete>
        <v-checkbox
          id="newNamespaceCheckbox"
          :model-value="newNamespace"
          label="Namespace does not exist yet"
          density="compact"
          color="primary"
          class="mt-1"
          hide-details
          :disabled="!namespaceNeeded"
          @update:model-value="$emit('update:newNamespace', !!$event)"
        />
      </v-col>
      <v-col cols="12" sm="6" md="6">
        <v-text-field
          id="secretName"
          :model-value="secretName"
          :label="secretNameRequired ? 'Secret name' : 'Secret name (optional)'"
          autocomplete="off"
          clearable
          variant="outlined"
          class="modern-input"
          color="primary"
          :rules="secretNameRequired ? rules.validDnsSubdomain : rules.optionalDnsSubdomain"
          :error-messages="secretNameError"
          :hint="
            secretNameRequired ? '' : 'Not sealed in this scope, only used in the generated YAML.'
          "
          persistent-hint
          @update:model-value="$emit('update:secretName', $event ?? '')"
        >
          <template #append-inner>
            <InfoTooltip class="ml-2">
              <span
                >Specify name of the secret.<br /><i
                  >The secret name must be of type: DNS Subdomain.</i
                ><template v-if="!secretNameRequired"
                  ><br /><i
                    >Only the "strict" scope binds the sealed secret to this name.</i
                  ></template
                ></span
              >
            </InfoTooltip>
          </template>
        </v-text-field>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import InfoTooltip from './InfoTooltip.vue'
import { SCOPES, scopeNeedsName, scopeNeedsNamespace } from '@/constants'
import { rules } from '@/utils/validation'

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
  secretNameError: {
    type: String,
    default: ''
  },
  favoriteNamespaces: {
    type: Set,
    required: true
  },
  newNamespace: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'update:namespaceName',
  'update:secretName',
  'update:scope',
  'update:newNamespace',
  'toggle-favorite'
])

const favoritesInList = computed(() =>
  props.namespaces.filter((namespace) => props.favoriteNamespaces.has(namespace))
)

// Favorites first, separated from the rest by a divider after the last one.
const sortedNamespaces = computed(() => [
  ...favoritesInList.value,
  ...props.namespaces.filter((namespace) => !props.favoriteNamespaces.has(namespace))
])

const lastFavoriteNamespace = computed(() => favoritesInList.value.at(-1) ?? null)

// Only the strict scope seals the secret for one specific name.
const secretNameRequired = computed(() => scopeNeedsName(props.scope))

// The namespace is irrelevant for cluster-wide secrets.
const namespaceNeeded = computed(() => scopeNeedsNamespace(props.scope))

// A new favorite moves to the favorites at the top of the list. Go there with
// it, so that the user sees where it went. (The list is virtual: the moved
// entry itself may not be rendered yet, so the list is scrolled, not the
// entry.) Removing a favorite happens at the top and needs no scrolling.
function toggleFavorite(namespace, event) {
  const becomesFavorite = !props.favoriteNamespaces.has(namespace)
  const list = event.currentTarget.closest('.v-list')
  emit('toggle-favorite', namespace)
  if (becomesFavorite) {
    list?.scrollTo({ top: 0 })
  }
}

function favoriteToggleLabel(namespace) {
  return props.favoriteNamespaces.has(namespace)
    ? `Remove ${namespace} from favorites`
    : `Add ${namespace} to favorites`
}
</script>

<style scoped>
/* Same emphasis and distance to the title as a plain prepend icon. */
.favorite-toggle {
  opacity: var(--v-medium-emphasis-opacity);
  margin-inline-end: 32px;
}
</style>
