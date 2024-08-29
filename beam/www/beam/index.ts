// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

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

const routes: RouteRecordRaw[] = [
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
		path: '/manufacture',
		name: 'manufacture',
		component: Manufacture,
	},
	{
		path: '/work_order/:orderId/',
		name: 'work_order',
		component: WorkOrder,
	},
	{
		path: '/job_card/:orderId/',
		name: 'job_card',
		component: JobCard,
	},
	{
		path: '/work_order/:orderId/operation/:id',
		name: 'operation',
		component: Operation,
	},
	{
		path: '/transfer',
		name: 'transfer',
		component: Transfer,
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
		path: '/repack',
		name: 'repack',
		component: Repack,
	},
	// {
	// 	path: '/workstation',
	// 	name: 'workstation',
	// 	component: Workstation,
	// },
]

const router = createRouter({
	history: createWebHashHistory(),
	routes,
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
