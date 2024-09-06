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
		meta: { doctype: null, view: 'list', requiresAuth: true },
	},
	{
		path: '/workstation',
		name: 'workstation',
		component: Workstation,
		meta: { doctype: 'Workstation', view: 'list', requiresAuth: true },
	},
	{
		path: '/work_order/:orderId/',
		name: 'work_order',
		component: WorkOrder,
		meta: { doctype: 'Work Order', view: 'form', requiresAuth: true },
	},
	{
		path: '/job_card/:orderId/',
		name: 'job_card',
		component: JobCard,
		meta: { doctype: 'Job Card', view: 'form', requiresAuth: true },
	},
	{
		path: '/work_order/:orderId/operation/:id',
		name: 'operation',
		component: Operation,
		meta: { doctype: 'Operation', view: 'form', requiresAuth: true },
	},
	{
		path: '/receive',
		name: 'receive',
		component: Receive,
		meta: { doctype: 'Purchase Order', view: 'list', requiresAuth: true },
	},
	{
		path: '/ship',
		name: 'ship',
		component: Ship,
		meta: { doctype: 'Delivery Note', view: 'list', requiresAuth: true },
	},
	{
		path: '/transfer',
		name: 'transfer',
		component: Transfer,
		meta: { doctype: 'Stock Entry', view: 'list', requiresAuth: true },
	},
	{
		path: '/manufacture',
		name: 'manufacture',
		component: Manufacture,
		meta: { doctype: 'Work Order', view: 'list', requiresAuth: true },
	},
	{
		path: '/repack',
		name: 'repack',
		component: Repack,
		meta: { doctype: 'Stock Entry', view: 'list', requiresAuth: true },
	},
]

export default routes
