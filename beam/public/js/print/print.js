// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Entry', {
	refresh(frm) {
		custom_print_button(frm)
	},
})
frappe.ui.form.on('Stock Reconciliation', {
	refresh(frm) {
		custom_print_button(frm)
	},
})
frappe.ui.form.on('Purchase Invoice', {
	refresh(frm) {
		if (frm.doc.update_stock) {
			custom_print_button(frm)
		}
	},
})
frappe.ui.form.on('Purchase Receipt', {
	refresh(frm) {
		custom_print_button(frm)
	},
})
frappe.ui.form.on('Sales Invoice', {
	refresh(frm) {
		if (frm.doc.update_stock) {
			custom_print_button(frm)
		}
	},
})
frappe.ui.form.on('Delivery Note', {
	refresh(frm) {
		custom_print_button(frm)
	},
})

function custom_print_button(frm) {
	if (frm.doc.docstatus != 1) {
		return
	}
	const beam_settings = frappe.boot.beam?.settings?.[frm.doc.company]
	if (!beam_settings?.enable_handling_units) {
		return
	}
	frm.add_custom_button(__('<span class="fa fa-print"></span> Print Handling Unit'), () => {
		let d = new frappe.ui.Dialog({
			title: __('Select Printer Setting'),
			fields: [
				{
					label: __('Printer Setting'),
					fieldname: 'printer_setting',
					fieldtype: 'Link',
					options: 'Network Printer Settings',
					default: frappe.defaults.get_user_default('Network Printer Settings'),
				},
				{
					label: __('Print Format'),
					fieldname: 'print_format',
					fieldtype: 'Link',
					options: 'Print Format',
					default: frappe.boot.beam?.default_hu_print_format,
					get_query: function () {
						return {
							filters: { doc_type: 'Handling Unit' },
						}
					},
				},
			],
			primary_action_label: 'Select',
			primary_action(selection) {
				d.hide()
				frappe.call({
					method: 'beam.beam.printing.print_handling_units',
					args: {
						doctype: frm.doc.doctype,
						name: frm.doc.name,
						printer_setting: selection.printer_setting,
						print_format: selection.print_format,
						doc: frm.doc,
					},
				})
			},
		})
		d.show()
	})
}
