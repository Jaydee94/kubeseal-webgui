import { createApp } from 'vue'
import App from './App.vue'
import BootstrapVue3 from 'bootstrap-vue-3'
import BootstrapIcon from '@dvuckovic/vue3-bootstrap-icons'

const app = createApp(App)

app.config.productionTip = false

import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue-3/dist/bootstrap-vue-3.css'
import 'bootstrap-dark-5/dist/css/bootstrap-nightshade.css'


if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
  document.documentElement.classList.add("dark");
}

app.use(BootstrapVue3)
app.use(BootstrapIcon)

app.mount('#app')
