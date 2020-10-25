import Vue from 'vue'
import App from './App.vue'
import { BootstrapVue, BootstrapVueIcons, LayoutPlugin } from 'bootstrap-vue'

Vue.config.productionTip = false

Vue.use(BootstrapVue)
Vue.use(BootstrapVueIcons)
Vue.use(LayoutPlugin)

Vue.filter('uppercase', function (value) {
	return value.toUpperCase()
})

new Vue({
  render: h => h(App),
}).$mount('#app')
