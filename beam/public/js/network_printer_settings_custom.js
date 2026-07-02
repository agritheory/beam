// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

let printers_cache = []
let pending_printer_name = null

function set_location_from_cache(frm, printer_name) {
	const match = printers_cache.find(p => p.value === printer_name)
	frm.set_value('printer_location', match ? match.location || '' : '')
}

frappe.ui.form.on('Network Printer Settings', {
	after_save(frm) {
		// Refresh cache from CUPS so subsequent printer_name changes
		// reflect the just-saved location, not stale pre-load data.
		printers_cache = []
		frm.trigger('connect_print_server')
	},
	connect_print_server(frm) {
		if (frm.doc.server_ip && frm.doc.port) {
			frappe.call({
				doc: frm.doc,
				method: 'get_printers_list',
				args: {
					ip: frm.doc.server_ip,
					port: frm.doc.port,
				},
				callback(data) {
					printers_cache = data.message || []
					frm.fields_dict.printer_name.set_data(printers_cache)
					// Resolve any pending printer_name lookup that fired before cache was ready
					if (pending_printer_name) {
						set_location_from_cache(frm, pending_printer_name)
						pending_printer_name = null
					}
				},
			})
		}
	},
	printer_name(frm) {
		if (!frm.doc.printer_name) {
			return
		}
		if (!printers_cache.length) {
			// Cache not populated yet — queue the lookup and trigger a fetch
			pending_printer_name = frm.doc.printer_name
			frm.trigger('connect_print_server')
			return
		}
		set_location_from_cache(frm, frm.doc.printer_name)
	},
})
