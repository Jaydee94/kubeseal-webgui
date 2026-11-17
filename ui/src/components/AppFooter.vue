<template>
  <!-- Part of the page, after the content: never fixed to the viewport, so it
       cannot cover the Encrypt button or an open dropdown. -->
  <footer class="app-footer">
    <div class="app-footer__inner">
      <div class="app-footer__brand">
        <v-icon icon="mdi-lock-outline" size="small" color="primary" />
        <span>Kubeseal WebGui</span>
      </div>

      <div class="app-footer__status" aria-live="polite">
        <template v-if="fetchConfigsSuccessful">
          <span class="status-dot status-dot--ok" aria-hidden="true" />
          <dl class="version-pills">
            <div v-for="(value, key) in configs" :key="key" class="version-pill">
              <dt>{{ labels[key] ?? key }}</dt>
              <dd>{{ value }}</dd>
            </div>
          </dl>
        </template>
        <template v-else-if="fetchConfigsSuccessful === false">
          <span class="status-dot status-dot--error" aria-hidden="true" />
          <span class="status-message">Could not retrieve application properties.</span>
        </template>
        <template v-else>
          <v-icon class="rotating" icon="mdi-loading" size="x-small" aria-hidden="true" />
          <span class="status-message">Loading application properties.</span>
        </template>
      </div>

      <v-btn
        :href="REPOSITORY_URL"
        target="_blank"
        rel="noopener noreferrer"
        icon
        variant="text"
        size="small"
        class="app-footer__github"
        aria-label="GitHub repository (opens in a new tab)"
      >
        <v-icon icon="mdi-github" />
        <v-tooltip activator="parent" location="top">GitHub repository</v-tooltip>
      </v-btn>
    </div>
  </footer>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchApiConfig } from '@/api'
import { loadConfig } from '@/config'
import { createLogger } from '@/utils/logger'

const log = createLogger('AppFooter')

const REPOSITORY_URL = 'https://github.com/Jaydee94/kubeseal-webgui'

// Readable names for the properties; an unknown one is shown under its own key.
const labels = {
  kubesealVersion: 'kubeseal',
  uiVersion: 'UI',
  apiVersion: 'API'
}

// The properties shown as pills, in this order.
const configs = ref({})
// null while loading, afterwards whether loading worked.
const fetchConfigsSuccessful = ref(null)

// Loaded once when the page loads; config.json is requested only once.
onMounted(async () => {
  try {
    const { uiVersion, apiVersion } = await loadConfig()
    configs.value = { ...(await fetchApiConfig()), uiVersion, apiVersion }
    fetchConfigsSuccessful.value = true
  } catch (error) {
    log.error('Could not retrieve application properties:', error)
    fetchConfigsSuccessful.value = false
  }
})
</script>

<style scoped>
/* Understated, like the header: only a hairline (the theme's border colour,
   dark on light and light on dark) sets it off from the page, the text is
   muted. */
.app-footer {
  margin-top: 8px;
  padding: 14px 16px calc(14px + env(safe-area-inset-bottom));
  border-top: 1px solid var(--line);
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  font-size: 0.75rem;
}

/* Same width as the content above it. */
.app-footer__inner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  max-width: 960px;
  margin: 0 auto;
}

.app-footer__brand {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-right: auto;
  font-weight: 500;
  letter-spacing: 0.02em;
}

.app-footer__status {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

/* On a phone the pills get a row of their own below brand and link. */
@media (max-width: 599px) {
  .app-footer__status {
    order: 3;
    flex-basis: 100%;
    flex-wrap: wrap;
  }
}

.app-footer__github {
  /* The icon is the same size as the text around it, not a toolbar button. */
  margin-right: -6px;
}

/* A dot says at a glance whether the properties could be loaded; the text
   next to it (or the pills) says it for everyone else. */
.status-dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot--ok {
  background: rgb(var(--v-theme-success));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-success), 0.18);
}

.status-dot--error {
  background: rgb(var(--v-theme-warning));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-warning), 0.22);
}

/* Segmented key/value badges: `kubeseal | 0.41.2`. */
.version-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
}

.version-pill {
  display: inline-flex;
  align-items: stretch;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius-full);
  background: rgba(var(--v-theme-on-surface), 0.04);
  line-height: 1.4;
}

.version-pill dt,
.version-pill dd {
  margin: 0;
  padding: 2px 8px;
}

.version-pill dt {
  padding-left: 10px;
}

.version-pill dd {
  padding-right: 10px;
  border-left: 1px solid var(--line);
  background: rgba(var(--v-theme-on-surface), 0.04);
  color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
  font-family: var(--font-mono);
  overflow-wrap: anywhere;
}

.status-message {
  min-width: 0;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.rotating {
  animation: rotate 1s linear infinite;
}

/* A spinner that never moves still says "loading" through its text. */
@media (prefers-reduced-motion: reduce) {
  .rotating {
    animation: none;
  }
}
</style>
