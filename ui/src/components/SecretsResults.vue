<template>
  <div>
    <v-row>
      <v-col>
        <SealedSecretCard
          ref="sealedSecretCardRef"
          :secret-name="secretName"
          :namespace-name="namespaceName"
          :sealed-secrets-annotations="sealedSecretsAnnotations"
          :rendered-secrets="renderedSecrets"
          :is-copied="isCopiedMain"
          :clipboard-available="clipboardAvailable"
          @copy="$emit('copy-main')"
        />
      </v-col>
    </v-row>
    <v-row
      dense
      align-content="center"
      class="mt-4"
    >
      <v-col
        v-for="(secret, counter) in sealedSecrets"
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
import { ref } from 'vue'
import SealedSecretCard from './SealedSecretCard.vue'
import SecretKeyCard from './SecretKeyCard.vue'

defineProps({
  sealedSecrets: {
    type: Array,
    required: true
  },
  secretName: {
    type: String,
    default: ''
  },
  namespaceName: {
    type: String,
    default: ''
  },
  sealedSecretsAnnotations: {
    type: String,
    required: true
  },
  renderedSecrets: {
    type: String,
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

// Expose ref for parent component to access
defineExpose({ sealedSecretCardRef })
</script>
