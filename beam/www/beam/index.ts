import { createApp } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'


import { makeServer } from './mocks/mirage'
import {
	ActionFooter,
	BeamModal,
	BeamModalOutlet,
	Confirm,
	ItemCheck,
	ItemCount,
	ListAnchor,
	ListItem,
	ListView,
	Navbar,
	ScanInput,
} from '@stonecrop/beam'
import PortalVue from 'portal-vue'

import Beam from './Beam.vue'
import Home from './pages/Home.vue'
import Workstation from './pages/Workstation.vue'
import WorkOrder from './pages/WorkOrder.vue'
import Receive from './pages/Receive.vue'
import Ship from './pages/Ship.vue'
import Transfer from './pages/Transfer.vue'
import Manufacture from './pages/Manufacture.vue'
import Repack from './pages/Repack.vue'

if (import.meta.env.VITE_SERVER) {
	makeServer()
}

const routes = [
	{
		path: '/',
		name: 'home',
		component: Home,
	},
	{
		path: '',
		name: 'home',
		component: Home,
	},
	{
		path: '/workstation',
		name: 'workstation',
		component: Workstation,
	},
	{
		path: '/work_order',
		name: 'work_order',
		component: WorkOrder,
	},
	{
		path: '/receive',
		name: 'receive',
		component: Receive,
	},
	{
		path: '/ship',
		name: 'ship',
		component: Ship,
	},
	{
		path: '/transfer',
		name: 'transfer',
		component: Transfer,
	},
	{
		path: '/manufacture',
		name: 'manufacture',
		component: Manufacture,
	},
	{
		path: '/repack',
		name: 'repack',
		component: Repack,
	},
]

const router = createRouter({
	history: createMemoryHistory(),
	routes,
})

const app = createApp(Beam)

app.use(router)
app.use(PortalVue)

app.component('ActionFooter', ActionFooter)
app.component('BeamModal', BeamModal)
app.component('BeamModalOutlet', BeamModalOutlet)
app.component('Confirm', Confirm)
app.component('ItemCheck', ItemCheck)
app.component('ItemCount', ItemCount)
app.component('ListAnchor', ListAnchor)
app.component('ListItem', ListItem)
app.component('ListView', ListView)
app.component('Navbar', Navbar)
app.component('ScanInput', ScanInput)
app.mount('#beam')
