import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import App from './App.vue'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { aliases, mdi } from 'vuetify/iconsets/mdi'

import "@fontsource/roboto"
import 'vuetify/styles' // Global CSS has to be imported
import '@mdi/font/css/materialdesignicons.css' // Ensure you are using css-loader
import './assets/styles.css' // Import custom global styles

const app = createApp(App)
const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi,
    }
  },
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        dark: false,
        colors: {
          primary: '#007bff',
          secondary: '#fd7e14',
          accent: '#17a2b8',
          error: '#fd7e14',
          info: '#0dcaf0',
          success: '#28a745',
          warning: '#ffc107',
          background: '#f8f9fa',
          surface: '#ffffff',
          'on-surface': '#212529',
          'surface-variant': '#e9ecef',
          'on-surface-variant': '#495057',
        }
      },
      dark: {
        dark: true,
        colors: {
          primary: '#3d94f6',
          secondary: '#fd8c3c',
          accent: '#20c997',
          error: '#fd8c3c',
          info: '#0dcaf0',
          success: '#28a745',
          warning: '#ffc107',
          background: '#212529',
          surface: '#343a40',
          'on-surface': '#f8f9fa',
          'surface-variant': '#495057',
          'on-surface-variant': '#adb5bd',
        }
      }
    }
  }
})

app
  .use(vuetify)
  .mount('#app')
