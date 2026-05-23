import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import App from './App.vue'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { aliases, mdi } from 'vuetify/iconsets/mdi'

import "@fontsource/roboto"
import "@fontsource/roboto-mono"
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
          primary: '#1F5E8B',
          secondary: '#F5933F',
          accent: '#E8821F',
          error: '#C62828',
          info: '#1976A8',
          success: '#2E7D32',
          warning: '#B8860B',
          background: '#F4F6F8',
          surface: '#FFFFFF',
          'surface-variant': '#E3E8EC',
          'on-surface': '#1A2230',
          'on-surface-variant': '#4A5564',
          'on-primary': '#FFFFFF',
          'on-secondary': '#1A2230',
          'on-error': '#FFFFFF',
          'on-success': '#FFFFFF',
          'on-warning': '#1A2230',
          'on-info': '#FFFFFF',
        }
      },
      dark: {
        dark: true,
        colors: {
          primary: '#5BA3D0',
          secondary: '#F5A45C',
          accent: '#F5A45C',
          error: '#EF5350',
          info: '#4FC3F7',
          success: '#66BB6A',
          warning: '#F0A202',
          background: '#0F141A',
          surface: '#1A222C',
          'surface-variant': '#28323E',
          'on-surface': '#E6EBF0',
          'on-surface-variant': '#9AA7B4',
          'on-primary': '#07111A',
          'on-secondary': '#1A1206',
          'on-error': '#1A0707',
          'on-success': '#07140A',
          'on-warning': '#1A1402',
          'on-info': '#04161F',
        }
      }
    }
  }
})

app
  .use(vuetify)
  .mount('#app')
