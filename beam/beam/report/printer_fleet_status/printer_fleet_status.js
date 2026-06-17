// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.query_reports['Printer Fleet Status'] = {
	filters: [
		{
			fieldname: 'server_ip',
			label: __('Server IP'),
			fieldtype: 'Data',
		},
	],
}
