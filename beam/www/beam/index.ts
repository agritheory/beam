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
import { createApp } from 'vue'
import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'

import Beam from './Beam.vue'
import { makeServer } from './mocks/mirage'
import Home from './pages/Home.vue'
import Workstation from './pages/Workstation.vue'
import WorkOrder from './pages/WorkOrder.vue'
import Receive from './pages/Receive.vue'
import Ship from './pages/Ship.vue'
import Transfer from './pages/Transfer.vue'
import Manufacture from './pages/Manufacture.vue'
import Repack from './pages/Repack.vue'
import JobCard from './pages/JobCard.vue'
import Operation from './pages/Operation.vue'

if (import.meta.env.DEV) {
	makeServer()
}

declare const frappe: any

const routes: RouteRecordRaw[] = [
	{
		path: '/',
		name: 'home',
		component: Home,
		meta: { requiresAuth: true },
	},
	{
		path: '',
		name: 'home',
		component: Home,
		meta: { requiresAuth: true },
	},
	{
		path: '/workstation',
		name: 'workstation',
		component: Workstation,
		meta: { requiresAuth: true },
	},
	{
		path: '/work_order',
		name: 'work_order',
		component: WorkOrder,
		meta: { requiresAuth: true },
	},
	{
		path: '/job_card/:id',
		name: 'job_card',
		component: JobCard,
		meta: { requiresAuth: true },
	},
	{
		path: '/work_order/:workOrder/operation/:id',
		name: 'operation',
		component: Operation,
		meta: { requiresAuth: true },
	},
	{
		path: '/receive',
		name: 'receive',
		component: Receive,
		meta: { requiresAuth: true },
	},
	{
		path: '/ship',
		name: 'ship',
		component: Ship,
		meta: { requiresAuth: true },
	},
	{
		path: '/transfer',
		name: 'transfer',
		component: Transfer,
		meta: { requiresAuth: true },
	},
	{
		path: '/manufacture',
		name: 'manufacture',
		component: Manufacture,
		meta: { requiresAuth: true },
	},
	{
		path: '/repack',
		name: 'repack',
		component: Repack,
		meta: { requiresAuth: true },
	},
]

const router = createRouter({
	history: createWebHashHistory(),
	routes,
})

router.beforeEach((to, from, next) => {
	if (to.meta && to.meta.requiresAuth) {
		if (frappe.user == 'Guest') {
			next(false)
			window.location.href = '/login'
		} else {
			next()
		}
	} else {
		next()
	}
})

const app = createApp(Beam)
app.use(router)
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
