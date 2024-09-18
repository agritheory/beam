// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import type { RouteRecordRaw } from 'vue-router'

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

const routes: RouteRecordRaw[] = [
	{
		path: '/',
		name: 'home',
		component: Home,
		meta: { requiresAuth: true, doctype: null, view: 'list' },
	},
	{
		path: '/workstation',
		name: 'workstation',
		component: Workstation,
		meta: { requiresAuth: true, doctype: 'Workstation', view: 'list' },
	},
	{
		path: '/work_order/:orderId/',
		name: 'work_order',
		component: WorkOrder,
		meta: { requiresAuth: true, doctype: 'Work Order', view: 'form' },
	},
	{
		path: '/job_card/:orderId/',
		name: 'job_card',
		component: JobCard,
		meta: { requiresAuth: true, doctype: 'Work Order', view: 'form' },
	},
	{
		path: '/work_order/:orderId/operation/:id',
		name: 'operation',
		component: Operation,
		meta: { requiresAuth: true, doctype: 'Work Order', view: 'form' },
	},
	{
		path: '/receive',
		name: 'receive',
		component: Receive,
		meta: { requiresAuth: true, doctype: 'Purchase Receipt', view: 'list' },
	},
	{
		path: '/ship',
		name: 'ship',
		component: Ship,
		meta: { requiresAuth: true, doctype: 'Delivery Note', view: 'list' },
	},
	{
		path: '/transfer',
		name: 'transfer',
		component: Transfer,
		meta: { requiresAuth: true, doctype: 'Stock Entry', view: 'list' },
	},
	{
		path: '/manufacture',
		name: 'manufacture',
		component: Manufacture,
		meta: { requiresAuth: true, doctype: 'Work Order', view: 'list' },
	},
	{
		path: '/repack',
		name: 'repack',
		component: Repack,
		meta: { requiresAuth: true, doctype: 'Stock Entry', view: 'list' },
	},
]

export default routes
