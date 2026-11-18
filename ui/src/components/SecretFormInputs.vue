<template>
  <div>
    <!-- First, because it decides what the fields below need: the namespace
         and the secret name. -->
    <div class="scope-picker mb-5">
      <div class="d-flex align-center mb-2">
        <span id="scopeLabel" class="eyebrow">Scope</span>
        <InfoTooltip class="ml-1 info-icon">
          <span
            >Specify the scope of the secret.<br /><i
              >The scope decides where the sealed secret can be unsealed.</i
            ></span
          >
        </InfoTooltip>
      </div>
      <div class="scope-picker__row">
        <v-btn-toggle
          :model-value="scope"
          mandatory
          variant="text"
          color="primary"
          density="comfortable"
          class="scope-toggle"
          role="group"
          aria-labelledby="scopeLabel"
          @update:model-value="$emit('update:scope', $event)"
        >
          <v-btn
            v-for="option in SCOPES"
            :key="option"
            :value="option"
            :data-scope="option"
            :aria-pressed="scope === option"
            class="scope-button"
            >{{ option }}</v-btn
          >
        </v-btn-toggle>
        <div id="scopeDescription" class="scope-description text-body-2" aria-live="polite">
          {{ SCOPE_DESCRIPTIONS[scope] }}
        </div>
      </div>
    </div>
    <v-row dense class="target-fields">
      <v-col cols="12" sm="6">
        <v-text-field
          v-if="newNamespace"
          id="namespaceSelection"
          :model-value="namespaceName"
          label="New namespace name"
          density="comfortable"
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
            <InfoTooltip class="ml-2 info-icon">
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
          :items="namespaceItems"
          label="Namespace name"
          density="comfortable"
          autocomplete="off"
          auto-select-first
          variant="outlined"
          class="modern-input"
          color="primary"
          :disabled="!namespaceNeeded"
          :error-messages="visibleNamespaceError"
          hide-details="auto"
          @update:model-value="$emit('update:namespaceName', $event)"
          @blur="namespaceTouched = true"
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
          </template>
          <template #append-inner>
            <InfoTooltip class="ml-2 info-icon">
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
      <v-col cols="12" sm="6">
        <v-text-field
          id="secretName"
          :model-value="secretName"
          :label="secretNameRequired ? 'Secret name' : 'Secret name (optional)'"
          density="comfortable"
          autocomplete="off"
          clearable
          variant="outlined"
          class="modern-input"
          color="primary"
          :error-messages="visibleSecretNameError"
          :hint="
            secretNameRequired ? '' : 'Not sealed in this scope, only used in the generated YAML.'
          "
          persistent-hint
          @update:model-value="$emit('update:secretName', $event ?? '')"
          @blur="secretNameTouched = true"
        >
          <template #append-inner>
            <InfoTooltip class="ml-2 info-icon">
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
        <v-btn
          v-if="secretNameSuggestion"
          id="secretNameSuggestion"
          class="secret-name-suggestion mt-1"
          size="small"
          variant="tonal"
          color="primary"
          prepend-icon="mdi-auto-fix"
          @click="$emit('update:secretName', secretNameSuggestion)"
        >
          Use <code class="ml-1">{{ secretNameSuggestion }}</code>
        </v-btn>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import InfoTooltip from './InfoTooltip.vue'
import {
  SCOPE_CLUSTER_WIDE,
  SCOPE_NAMESPACE_WIDE,
  SCOPE_STRICT,
  SCOPES,
  scopeNeedsName,
  scopeNeedsNamespace
} from '@/constants'
import { firstRuleMessage, isDnsSubdomain, rules, toDnsSubdomain } from '@/utils/validation'

const SCOPE_DESCRIPTIONS = {
  [SCOPE_STRICT]: 'Bound to this name and namespace',
  [SCOPE_NAMESPACE_WIDE]: 'Any name within this namespace',
  [SCOPE_CLUSTER_WIDE]: 'Any name in any namespace'
}

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

// Favorites first. With favorites, both groups get a heading; the
// autocomplete drops the heading of a group whose entries are all filtered out.
const namespaceItems = computed(() => {
  if (!favoritesInList.value.length) return props.namespaces
  const others = props.namespaces.filter((namespace) => !props.favoriteNamespaces.has(namespace))
  return [
    { type: 'subheader', title: 'Favorites' },
    ...favoritesInList.value,
    // Without any other namespace the heading would have nothing below it.
    ...(others.length ? [{ type: 'subheader', title: 'All namespaces' }, ...others] : [])
  ]
})

// Only the strict scope seals the secret for one specific name.
const secretNameRequired = computed(() => scopeNeedsName(props.scope))

// A field that was never visited must not complain about being empty. A name
// that is being typed is validated right away, an empty one only after the
// field was left. Own state instead of Vuetify's `rules`: those do not rerun
// when the scope switches between required and optional, which left the
// message of the other mode behind.
const secretNameTouched = ref(false)

const visibleSecretNameError = computed(() => {
  if (!secretNameTouched.value && !props.secretName) return ''
  return firstRuleMessage(
    secretNameRequired.value ? rules.validDnsSubdomain : rules.optionalDnsSubdomain,
    props.secretName
  )
})

// The namespace of the list is never invalid, only missing: reported after the
// field was left or Encrypt was tried (a new namespace has its own rules).
const namespaceTouched = ref(false)

const visibleNamespaceError = computed(() =>
  namespaceTouched.value && namespaceNeeded.value && !props.namespaceName ? 'Must not be empty' : ''
)

// What the fields would show after they were visited, for a form that the user
// tried to submit without having visited them all.
defineExpose({
  showErrors() {
    secretNameTouched.value = true
    namespaceTouched.value = true
  }
})

// Offer the closest valid name for an invalid one, but only once the field was
// left: while typing, every half-finished name ("my-secret-") is invalid.
const secretNameSuggestion = computed(() =>
  secretNameTouched.value && props.secretName && !isDnsSubdomain(props.secretName)
    ? toDnsSubdomain(props.secretName)
    : ''
)

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
.scope-picker__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
}

/* A segmented control: a recessed track with the chosen option raised. */
.scope-toggle {
  max-width: 100%;
  height: auto;
  flex-wrap: wrap;
  padding: 3px;
  gap: 2px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--inset-bg);
}

.scope-button {
  text-transform: none;
  letter-spacing: normal;
  font-size: 0.8125rem;
  font-weight: 500;
  padding-inline: 12px;
  min-width: 0;
  /* A comfortable touch target. */
  min-height: 32px;
  border-radius: 7px !important;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.scope-button.v-btn--active {
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-primary));
  box-shadow:
    0 1px 2px rgba(16, 24, 40, 0.12),
    0 0 0 1px var(--line);
}

.v-theme--dark .scope-button.v-btn--active {
  background: rgba(255, 255, 255, 0.09);
}

/* The raised look says "chosen"; Vuetify's tint on top would muddy it. */
.scope-button.v-btn--active :deep(.v-btn__overlay) {
  opacity: 0;
}

.scope-description {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.info-icon {
  opacity: 0.7;
}

/* A message that goes away (the name became valid) must go at once: Vuetify
   fades it out while it still overlaps the next content, which looks like a
   message that sticks around. This also covers reduced motion. */
:deep(.v-messages__message.slide-y-transition-leave-active) {
  transition: none;
}

/* Same emphasis and distance to the title as a plain prepend icon. */
.favorite-toggle {
  opacity: var(--v-medium-emphasis-opacity);
  margin-inline-end: 32px;
}
</style>
