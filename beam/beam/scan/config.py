import frappe


@frappe.whitelist()
def get_scan_doctypes():
	pass
	# get hooks with override or return  this as a default
	"""
	{
		'listview': [
			'Item',
			'Warehouse',
			'Handling Unit',
			'Packing Slip',
			'Purchase Receipt',
			'Purchase Invoice',
			'Delivery Note',
			'Sales Invoice',
			'Stock Entry',
			'Stock Reconciliation',
		],
		'frm': [
			'Purchase Receipt',
			'Purchase Invoice',
			'Delivery Note',
			'Packing Slip',
			'Sales Invoice',
			'Stock Entry',
			'Stock Reconciliation',
		],
	}
	"""
