// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Entry', {
	async before_cancel(frm) {
		await set_recombine_handling_units(frm)
	},
	setup: function (frm) {
		frm.set_query('handling_unit', 'items', function (doc, cdt, cdn) {
			let row = locals[cdt][cdn]
			if (!row.item_code) {
				return
			}
			return {
				query: 'beam.beam.overrides.stock_entry.get_handling_units_for_item_code',
				filters: {
					item_code: row.item_code,
				},
			}
		})
	},
})

async function show_handling_unit_recombine_dialog(frm) {
	const data = await get_handling_units(frm)
	if (!data || !data.length) {
		return []
	}
	let fields = [
		{
			fieldtype: 'Data',
			fieldname: 'row_name',
			in_list_view: 0,
			read_only: 1,
			disabled: 0,
			hidden: 1,
		},
		{
			fieldtype: 'Data',
			fieldname: 'target_row_name',
			in_list_view: 0,
			read_only: 1,
			disabled: 0,
			hidden: 1,
		},
		{
			fieldtype: 'Link',
			fieldname: 'item_code',
			options: 'Item',
			in_list_view: 1,
			read_only: 1,
			disabled: 0,
			label: __('Item Code'),
			columns: 2,
		},
		{
			fieldtype: 'Data',
			fieldname: 'item_name',
			in_list_view: 0,
			disabled: 0,
			hidden: 1,
		},
		{
			fieldtype: 'Data',
			fieldname: 'handling_unit',
			label: __('Handling Unit'),
			in_list_view: 1,
			read_only: 1,
			columns: 2,
		},
		{
			fieldtype: 'Float',
			fieldname: 'remaining_qty',
			label: __('Remaining Qty'),
			in_list_view: 1,
			read_only: 1,
			columns: 1,
		},
		{
			fieldtype: 'Data',
			fieldname: 'to_handling_unit',
			label: __('Handling Unit to recombine'),
			in_list_view: 1,
			read_only: 1,
			columns: 2,
		},
		{
			fieldtype: 'Float',
			fieldname: 'transferred_qty',
			label: __('Transferred Qty'),
			in_list_view: 1,
			read_only: 1,
			columns: 1,
		},
	]

	return new Promise(resolve => {
		let dialog = new frappe.ui.Dialog({
			title: __('Please select Handling Units to re-combine'),
			fields: [
				{
					fieldname: 'handling_units',
					fieldtype: 'Table',
					cannot_add_rows: true,
					cannot_delete_rows: false,
					reqd: 1,
					data: data,
					get_data: () => {
						return data
					},
					fields: fields,
					description: __(
						'Please select Handling Units to re-combine. Unselected Handling Units will be returned to inventory with their new quantities and Handling Units'
					),
				},
			],
			primary_action: () => {
				let selected = dialog.fields_dict.handling_units.grid.get_selected_children()
				let to_recombine = []
				for (let row of selected) {
					to_recombine.push(row.row_name)
					if (row.target_row_name) {
						to_recombine.push(row.target_row_name)
					}
				}
				dialog.hide()
				return resolve(to_recombine)
			},
			primary_action_label: __('Cancel and Recombine'),
			size: 'extra-large',
		})
		dialog.show()
		// Pre-check all rows so recombine is the default behavior
		setTimeout(() => {
			const grid = dialog.fields_dict.handling_units.grid
			// Enable and check all rows
			if (grid.wrapper) {
				grid.wrapper.find('.grid-row-check').prop('disabled', false).prop('checked', true)
				// Hide the Delete button
				grid.wrapper.find('.grid-remove-rows').hide()
			}
			grid.grid_rows?.forEach(row => {
				if (row.doc) {
					row.doc.__checked = 1
					if (row.row) {
						row.row.find('.grid-row-check').prop('disabled', false).prop('checked', true)
					}
				}
			})
			grid.refresh()
		}, 200)
		dialog.get_close_btn()
	})
}

async function get_handling_units(frm) {
	let handling_units = []
	const transfer_types = ['Material Transfer', 'Send to Subcontractor', 'Material Transfer for Manufacture']

	for (const row of frm.doc.items) {
		if (!row.handling_unit) continue

		if (transfer_types.includes(frm.doc.purpose)) {
			// Material Transfer types: source and destination HU are on the same row
			if (!row.to_handling_unit) continue
			let remaining_qty = await get_handling_unit_stock_qty(frm.doc.name, row.handling_unit, row.s_warehouse)
			handling_units.push({
				row_name: row.name,
				item_code: row.item_code,
				item_name: row.item_name,
				handling_unit: row.handling_unit,
				to_handling_unit: row.to_handling_unit,
				remaining_qty: remaining_qty,
				transferred_qty: row.qty,
			})
		} else {
			// Repack/Manufacture/etc: source and target HUs are on separate rows
			// Only show source rows (those with s_warehouse); pair with matching target row
			if (!row.s_warehouse) continue
			let target_row = frm.doc.items.find(r => r.t_warehouse && r.handling_unit && r.item_code === row.item_code)
			let remaining_qty = await get_handling_unit_stock_qty(frm.doc.name, row.handling_unit, row.s_warehouse)
			handling_units.push({
				row_name: row.name,
				target_row_name: target_row?.name || '',
				item_code: row.item_code,
				item_name: row.item_name,
				handling_unit: row.handling_unit,
				to_handling_unit: target_row?.handling_unit || '',
				remaining_qty: remaining_qty,
				transferred_qty: row.transfer_qty || row.qty,
			})
		}
	}

	return handling_units
}
async function get_handling_unit_stock_qty(name, handling_unit, s_warehouse) {
	let result = await frappe.xcall('beam.beam.overrides.stock_entry.get_handling_unit_qty', {
		voucher_no: name,
		handling_unit: handling_unit,
		warehouse: s_warehouse,
	})
	return flt(result)
}

//re combine
async function set_recombine_handling_units(frm) {
	// const beam_settings = frappe.boot.beam?.settings?.[frm.doc.company]
	// if (!beam_settings?.enable_handling_units) {
	// 	return
	// }
	let to_recombine = await show_handling_unit_recombine_dialog(frm)
	await frappe.xcall('beam.beam.overrides.stock_entry.set_rows_to_recombine', {
		docname: frm.doc.name,
		to_recombine: to_recombine,
	})
}
