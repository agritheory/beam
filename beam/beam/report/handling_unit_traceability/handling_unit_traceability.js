// Copyright (c) 2023, AgriTheory and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['Handling Unit Traceability'] = {
	filters: [
		{
			fieldname: 'handling_unit',
			label: __('Handling Unit'),
			fieldtype: 'Link',
			options: 'Handling Unit',
		},
		{
			fieldname: 'delivery_note',
			label: __('Delivery Note'),
			fieldtype: 'Link',
			options: 'Delivery Note',
		},
		{
			fieldname: 'sales_invoice',
			label: __('Sales Invoice'),
			fieldtype: 'Link',
			options: 'Sales Invoice',
			get_query: function () {
				return {
					filters: {
						update_stock: 1,
					},
				}
			},
		},
	],
}
