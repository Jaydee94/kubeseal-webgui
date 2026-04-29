<template>
  <div>
    <!-- Multi-namespace results -->
    <template v-if="isMultiNamespace">
      <v-row v-for="(entry, idx) in renderedSecrets" :key="entry.namespace">
        <v-col>
          <SealedSecretCard
            :ref="el => { if (el) sealedSecretCardRefs[idx] = el }"
            :secret-name="secretName"
            :namespace-name="entry.namespace"
            :sealed-secrets-annotations="sealedSecretsAnnotations"
            :rendered-secrets="entry.rendered"
            :is-copied="copiedCards[idx] || false"
            :clipboard-available="clipboardAvailable"
            @copied="onCardCopied(idx)"
          />
        </v-col>
      </v-row>
    </template>

    <!-- Single namespace result -->
    <template v-else>
      <v-row>
        <v-col>
          <SealedSecretCard
            ref="sealedSecretCardRef"
            :secret-name="secretName"
            :namespace-name="singleNamespace"
            :sealed-secrets-annotations="sealedSecretsAnnotations"
            :rendered-secrets="renderedSecrets"
            :is-copied="isCopiedMain"
            :clipboard-available="clipboardAvailable"
            @copied="$emit('copy-main')"
          />
        </v-col>
      </v-row>
    </template>

    <v-row
      dense
      align-content="center"
      class="mt-4"
    >
      <v-col
        v-for="(secret, counter) in flatSealedSecrets"
        :key="counter"
        cols="12"
        sm="6"
        md="4"
      >
        <SecretKeyCard
          :secret-key="secret['key']"
          :secret-value="secret['value']"
          :is-copied="copiedIndividual[counter]"
          :clipboard-available="clipboardAvailable"
          @copy="$emit('copy-individual', counter)"
        />
      </v-col>
    </v-row>
    <v-row
      justify="center"
      class="mt-4"
    >
      <v-col
        cols="12"
        sm="6"
        md="4"
        class="d-flex justify-center gap-2"
      >
        <v-btn
          variant="outlined"
          color="primary"
          @click="$emit('clear')"
        >
          Clear
        </v-btn>
        <v-btn
          variant="outlined"
          color="secondary"
          @click="$emit('edit')"
        >
          Edit Secrets
        </v-btn>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SealedSecretCard from './SealedSecretCard.vue'
import SecretKeyCard from './SecretKeyCard.vue'

const props = defineProps({
  sealedSecrets: {
    type: Array,
    required: true
  },
  secretName: {
    type: String,
    default: ''
  },
  namespaceName: {
    type: Array,
    default: () => []
  },
  sealedSecretsAnnotations: {
    type: String,
    required: true
  },
  renderedSecrets: {
    type: [String, Array],
    required: true
  },
  clipboardAvailable: {
    type: Boolean,
    default: true
  },
  copiedIndividual: {
    type: Object,
    required: true
  },
  isCopiedMain: {
    type: Boolean,
    default: false
  }
})

defineEmits(['copy-main', 'copy-individual', 'clear', 'edit'])

const sealedSecretCardRef = ref(null)
const sealedSecretCardRefs = ref([])
const copiedCards = ref({})

const isMultiNamespace = computed(() => {
  return Array.isArray(props.renderedSecrets)
})

const singleNamespace = computed(() => {
  return props.namespaceName.length > 0 ? props.namespaceName[0] : ''
})

const flatSealedSecrets = computed(() => {
  if (Array.isArray(props.sealedSecrets) && props.sealedSecrets.length > 0 && props.sealedSecrets[0].namespace) {
    return props.sealedSecrets.flatMap(entry => entry.secrets)
  }
  return props.sealedSecrets
})

function onCardCopied(idx) {
  copiedCards.value[idx] = true
  setTimeout(() => {
    copiedCards.value[idx] = false
  }, 2000)
}

// Expose refs for parent component to access
defineExpose({ sealedSecretCardRef, sealedSecretCardRefs })
</script>
