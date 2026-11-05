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

function update_printer_default_checks(d) {
	const selected = d.get_value('printer_setting')
	const configured = frappe.boot.beam?.default_network_printer_settings
	const prefer_save = !!selected && !configured
	const prefer_session = !!selected && !!configured && selected !== configured
	d.set_value('save_as_default', prefer_save ? 1 : 0)
	d.set_value('set_session_default', prefer_session ? 1 : 0)
}

function apply_printer_defaults(selection) {
	const calls = []
	if (selection.save_as_default) {
		calls.push(
			frappe
				.call({
					method: 'beam.beam.printer_defaults.save_default_printer',
					args: { printer_setting: selection.printer_setting },
				})
				.then(r => {
					if (r.message) {
						frappe.boot.beam = frappe.boot.beam || {}
						frappe.boot.beam.default_network_printer_settings = r.message
					}
				})
		)
	}
	if (selection.set_session_default) {
		calls.push(
			frappe
				.call({
					method: 'beam.beam.printer_defaults.set_session_printer',
					args: { printer_setting: selection.printer_setting },
				})
				.then(() => {
					frappe.defaults.set_user_default_local('network_printer_settings', selection.printer_setting)
				})
		)
	}
	return Promise.all(calls)
}

frappe.provide('beam')

/**
 * Open the Network Printer Settings dialog with default-printer handling.
 *
 * @param {object} frm - the current form
 * @param {object} opts
 * @param {string} opts.method - whitelisted method that prints; receives `args` plus
 *   `printer_setting` and `print_format` from the dialog
 * @param {object} [opts.args] - extra arguments for `method`
 * @param {string} [opts.print_format_doctype] - limits Print Format choices to this DocType
 * @param {string} [opts.default_print_format] - preselected Print Format
 */
beam.print_dialog = function (frm, { method, args = {}, print_format_doctype, default_print_format } = {}) {
	if (!method) {
		frappe.throw(__('beam.print_dialog requires a method'))
	}
	let d = new frappe.ui.Dialog({
		title: __('Select Printer Setting'),
		fields: [
			{
				label: __('Printer Setting'),
				fieldname: 'printer_setting',
				fieldtype: 'Link',
				options: 'Network Printer Settings',
				default:
					frappe.defaults.get_user_default('Network Printer Settings') ||
					frappe.boot.beam?.default_network_printer_settings,
				onchange() {
					update_printer_default_checks(d)
				},
			},
			{
				label: __('Print Format'),
				fieldname: 'print_format',
				fieldtype: 'Link',
				options: 'Print Format',
				default: default_print_format,
				get_query: function () {
					return {
						filters: print_format_doctype ? { doc_type: print_format_doctype } : {},
					}
				},
			},
			{
				label: __('Save as my default printer'),
				fieldname: 'save_as_default',
				fieldtype: 'Check',
				default: 0,
			},
			{
				label: __('Set as session default'),
				fieldname: 'set_session_default',
				fieldtype: 'Check',
				default: 0,
			},
		],
		primary_action_label: 'Select',
		primary_action(selection) {
			d.hide()
			frappe.call({
				method: method,
				args: {
					...args,
					printer_setting: selection.printer_setting,
					print_format: selection.print_format,
				},
				callback() {
					apply_printer_defaults(selection)
				},
			})
		},
	})
	d.show()
	update_printer_default_checks(d)
	return d
}

function custom_print_button(frm) {
	if (frm.doc.docstatus != 1) {
		return
	}
	const beam_settings = frappe.boot.beam?.settings?.[frm.doc.company]
	if (!beam_settings?.enable_handling_units) {
		return
	}
	frm.add_custom_button(__('<span class="fa fa-print"></span> Print Handling Unit'), () => {
		beam.print_dialog(frm, {
			method: 'beam.beam.printing.print_handling_units',
			args: {
				doctype: frm.doc.doctype,
				name: frm.doc.name,
				doc: frm.doc,
			},
			print_format_doctype: 'Handling Unit',
			default_print_format: frappe.boot.beam?.default_hu_print_format,
		})
	})
}
