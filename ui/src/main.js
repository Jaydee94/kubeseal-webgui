import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import App from './App.vue'
import { aliases, mdi } from 'vuetify/iconsets/mdi'

import '@fontsource/roboto'
import 'vuetify/styles' // Global CSS has to be imported
import '@mdi/font/css/materialdesignicons.css' // Ensure you are using css-loader
import './assets/styles.css' // Import custom global styles
import { createLogger, getLogLevel } from './utils/logger'

const log = createLogger('app')

const app = createApp(App)
const vuetify = createVuetify({
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi
    }
  },
  // Calm defaults for every button: no shouting capitals, softer corners.
  defaults: {
    VBtn: { class: 'text-none', rounded: 'lg' },
    VChip: { rounded: 'lg' }
  },
  // Neutral slate surfaces carry the layout; the brand blue (actions) and
  // orange (attention) of the logo are kept as the only accents.
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        dark: false,
        colors: {
          primary: '#0a6cff',
          secondary: '#f07a1a',
          accent: '#17a2b8',
          error: '#e8590c',
          info: '#0b8bd9',
          success: '#1f9d55',
          warning: '#e0a100',
          background: '#f2f4f7',
          surface: '#ffffff',
          'on-surface': '#161b26',
          'surface-variant': '#e9ecf1',
          'on-surface-variant': '#4a5263'
        },
        variables: {
          'border-color': '#0f1729',
          'border-opacity': 0.1
        }
      },
      dark: {
        dark: true,
        colors: {
          primary: '#4c9dff',
          // Dark text on the light blue: white would only reach about 3:1.
          'on-primary': '#07111f',
          secondary: '#ff9447',
          accent: '#20c997',
          error: '#ff8a4c',
          info: '#38bdf8',
          success: '#3ecf8e',
          warning: '#f5c451',
          background: '#0d1117',
          surface: '#161b23',
          'on-surface': '#e8ebf1',
          'surface-variant': '#232a35',
          'on-surface-variant': '#a3acbb'
        },
        variables: {
          'border-color': '#ffffff',
          'border-opacity': 0.09
        }
      }
    }
  }
})

// Errors thrown in components (render, lifecycle hooks, event handlers) that
// nothing else caught. `info` names where in the component it happened.
app.config.errorHandler = (error, instance, info) => {
  log.error(`Unhandled error in ${instance?.$options?.__name || 'component'} (${info}):`, error)
}

log.info(`Starting UI (mode: ${import.meta.env.MODE}, log level: ${getLogLevel()})`)

app.use(vuetify).mount('#app')
