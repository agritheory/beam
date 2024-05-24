import { Model, createServer } from 'miragejs'

export function makeServer() {
	const server = createServer({
		environment: 'development',

		models: {
			workstation: Model,
		},

		seeds(server) {
			server.db.loadData({
				workstations: [
					{
						name: 'Mix Pie Crust Station',
						creation: '2024-05-17T07:00:55.612892',
						modified: '2024-05-17T07:00:55.612892',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Mix Pie Crust Station',
						production_capacity: 20,
						status: 'Production',
					},
					{
						name: 'Roll Pie Crust Station',
						creation: '2024-05-17T07:00:55.621654',
						modified: '2024-05-17T07:00:55.621654',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Roll Pie Crust Station',
						production_capacity: 20,
						status: 'Production',
					},
					{
						name: 'Make Pie Filling Station',
						creation: '2024-05-17T07:00:55.624575',
						modified: '2024-05-17T07:00:55.624575',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Make Pie Filling Station',
						production_capacity: 20,
						status: 'Production',
					},
					{
						name: 'Cooling Station',
						creation: '2024-05-17T07:00:55.627341',
						modified: '2024-05-17T07:00:55.627341',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Cooling Station',
						production_capacity: 100,
						status: 'Production',
					},
					{
						name: 'Box Pie Station',
						creation: '2024-05-17T07:00:55.630030',
						modified: '2024-05-17T07:00:55.630030',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Box Pie Station',
						production_capacity: 100,
						status: 'Production',
					},
					{
						name: 'Baking Station',
						creation: '2024-05-17T07:00:55.632714',
						modified: '2024-05-17T07:00:55.632714',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Baking Station',
						production_capacity: 20,
						status: 'Production',
					},
					{
						name: 'Assemble Pie Station',
						creation: '2024-05-17T07:00:55.635371',
						modified: '2024-05-17T07:00:55.635371',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Assemble Pie Station',
						production_capacity: 20,
						status: 'Production',
					},
					{
						name: 'Mix Pie Filling Station',
						creation: '2024-05-17T07:00:55.637963',
						modified: '2024-05-17T07:00:55.637963',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Mix Pie Filling Station',
						production_capacity: 20,
						status: 'Production',
					},
					{
						name: 'Packaging Station',
						creation: '2024-05-17T07:00:55.640581',
						modified: '2024-05-17T07:01:3,.19668',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Packaging Station',
						production_capacity: 2,
						status: 'Off',
					},
					{
						name: 'Cooling Racks Station',
						creation: '2024-05-17T07:00:55.651109',
						modified: '2024-05-17T07:01:3,.16712',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Cooling Racks Station',
						production_capacity: 80,
						status: 'Off',
					},
					{
						name: 'Oven Station',
						creation: '2024-05-17T07:00:55.656441',
						modified: '2024-05-17T07:01:3,.98321',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Oven Station',
						production_capacity: 20,
						status: 'Off',
					},
					{
						name: 'Refrigerator Station',
						creation: '2024-05-17T07:00:55.653796',
						modified: '2024-05-17T07:01:4,.747',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Refrigerator Station',
						production_capacity: 200,
						status: 'Off',
					},
					{
						name: 'Mixer Station',
						creation: '2024-05-17T07:00:55.659075',
						modified: '2024-05-17T07:01:4,.08439',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Mixer Station',
						production_capacity: 10,
						status: 'Off',
					},
					{
						name: 'Food Prep Table 2',
						creation: '2024-05-17T07:00:55.643166',
						modified: '2024-05-17T07:01:4,.00131',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Food Prep Table 2',
						production_capacity: 10,
						status: 'Off',
					},
					{
						name: 'Range Station',
						creation: '2024-05-17T07:00:55.648422',
						modified: '2024-05-17T07:01:5,.55463',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Range Station',
						production_capacity: 20,
						status: 'Off',
					},
					{
						name: 'Food Prep Table 1',
						creation: '2024-05-17T07:00:55.645775',
						modified: '2024-05-17T07:01:5,.58652',
						modified_by: 'Administrator',
						owner: 'Administrator',
						workstation_name: 'Food Prep Table 1',
						production_capacity: 5,
						status: 'Off',
					},
				],
			})
		},

		routes() {
			this.namespace = 'api'
			this.get('/workstations', schema => {
				return schema.db.workstations
			})

			this.namespace = ''
			this.passthrough()
		},
	})

	return server
}
