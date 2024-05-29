import { createApp } from 'vue'

import Beam from './Beam.vue'
import { makeServer } from './mocks/mirage'

if (import.meta.env.DEV || import.meta.env.FRAPPE_DEV_MODE) {
	makeServer()
}

const app = createApp(Beam)
app.mount('#beam')
