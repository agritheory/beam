import frappe

def execute():
	default_config = [
		{
			"label": 'Manufacture',
			"route": '#/manufacture',
			"dt": 'Stock Entry',
			"component": "Manufacture"
		},
		{
			"label": 'Demand',
			"route": '#/demand',
			"dt": 'Stock Entry',
			"component": "Demand"
		},
		{
			"label": 'Move',
			"route": '#/move',
			"dt": 'Stock Entry',
			"component": "Demand"
		},
		{
			"label": 'Receive',
			"route": '#/receive',
			"dt": 'Purchase Receipt',
			"component": "Receive"
		},
		{
			"label": 'Ship',
			"route": '#/ship',
			"dt": 'Delivery Note',
			"component": "Ship"
		},
		{
			"label": 'Repack',
			"route": '#/repack',
			"dt": 'Stock Entry',
			"component": "Repack"
		},
	]

	beam_configs = frappe.get_all('BEAM Settings', pluck="name")
	for company in beam_configs:
		doc = frappe.get_doc('BEAM Settings', company)
		if len(doc.routes) > 0:
			return
		for row in default_config:
			doc.append('routes', row)
		doc.save()



