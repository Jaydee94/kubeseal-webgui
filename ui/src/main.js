import Vue from 'vue'
import App from './App.vue'
import { BootstrapVue, BootstrapVueIcons, LayoutPlugin } from 'bootstrap-vue'
import ToggleButton from 'vue-js-toggle-button'

Vue.config.productionTip = false

import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'
import 'bootstrap-dark-4/dist/bootstrap-nightshade.css'
 


if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
  document.documentElement.classList.add("dark");
}

Vue.use(BootstrapVue)
Vue.use(BootstrapVueIcons)
Vue.use(LayoutPlugin)
Vue.use(ToggleButton)

new Vue({
  render: h => h(App),
}).$mount('#app')
