// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { JSONAPISerializer, Model, createServer } from 'miragejs'

import jobCards from './job_cards.json'
import workOrders from './work_orders.json'

export function makeServer() {
	const server = createServer({
		environment: 'development',

		models: {
			jobCard: Model,
			workOrder: Model,
		},

		serializers: {
			application: JSONAPISerializer,
		},

		seeds(server) {
			server.db.loadData({
				jobCards,
				workOrders,
			})
		},

		routes() {
			this.namespace = '/api/resource'

			this.get('/Job Card', (schema, request) => {
				let listData = schema.db.jobCards as any[]

				if (request.queryParams.filters) {
					const filters = JSON.parse(request.queryParams.filters.toString())

					listData = listData.filter(jobCard => {
						// assume operator is always '='
						for (const [field, operator, value] of filters) {
							if (jobCard[field] !== value) {
								return false
							}
						}
						return true
					})
				}

				if (request.queryParams.fields) {
					const fields = JSON.parse(request.queryParams.fields.toString())

					listData = listData.map(jobCard => {
						const data = {}
						for (const field of fields) {
							data[field] = jobCard[field]
						}
						return data
					})
				}

				return { data: listData }
			})

			this.get('/Job Card/:id', (schema, request) => {
				const data = schema.db.jobCards.findBy({ name: request.params.id })
				return { data }
			})

			this.get('/Work Order', (schema, request) => {
				let listData = schema.db.workOrders as any[]

				if (request.queryParams.order_by) {
					const [field, sort_operation] = request.queryParams.order_by.toString().split(' ')
					listData = listData.sort((a, b) => {
						const a_time = new Date(a[field]).getTime()
						const b_time = new Date(b[field]).getTime()

						if (sort_operation.toLowerCase() === 'asc') {
							return a_time - b_time
						} else if (sort_operation.toLowerCase() === 'desc') {
							return b_time - a_time
						}
					})
				}

				if (request.queryParams.fields) {
					const fields = JSON.parse(request.queryParams.fields.toString())

					listData = listData.map(workOrder => {
						const data = {}
						for (const field of fields) {
							data[field] = workOrder[field]
						}
						return data
					})
				}

				return { data: listData }
			})

			this.get('/Work Order/:id', (schema, request) => {
				const data = schema.db.workOrders.findBy({ name: request.params.id })
				return { data }
			})

			this.namespace = ''
			this.passthrough()
		},
	})

	return server
}
