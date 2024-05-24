import { createApp } from 'vue'

import Beam from './Beam.vue'
import { makeServer } from './mocks/mirage'

const server = makeServer()
const app = createApp(Beam)
app.mount('#beam')
