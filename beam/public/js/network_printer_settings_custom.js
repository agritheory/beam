// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

let printers_cache = []
let pending_printer_name = null

function set_location_from_cache(frm, printer_name) {
	const match = printers_cache.find(p => p.value === printer_name)
	frm.set_value('printer_location', match ? match.location || '' : '')
}

function load_ppds_for_dialog(server_ip, port, field) {
	return frappe
		.call({
			method: 'beam.beam.overrides.network_printer_settings.get_ppds',
			args: { server_ip, port },
		})
		.then(r => {
			field.set_data(r.message || [])
			return r.message || []
		})
}

function render_cups_status_dashboard(frm, status) {
	if (!status) {
		return
	}

	const color = status.indicator_color || 'green'
	const label = frappe.utils.escape_html(status.indicator_label || __('Unknown'))
	const make_model = frappe.utils.escape_html(status.make_model || '')
	const description = frappe.utils.escape_html(status.description || '')
	const accepting = status.is_accepting_jobs ? __('Accepting jobs') : __('Rejecting jobs')
	const reasons =
		status.state_reasons_display && status.state_reasons_display !== 'none'
			? frappe.utils.escape_html(status.state_reasons_display)
			: ''

	const lines = [`<span class="indicator ${color}"></span> ${label}`, make_model, description, accepting]
	if (reasons) {
		lines.push(reasons)
	}

	const html = `<div class="text-muted small">${lines.filter(Boolean).join('<br>')}</div>`

	if (!frm.cups_status_wrapper || !$.contains(document, frm.cups_status_wrapper[0])) {
		frm.cups_status_wrapper = $(
			`<div class="cups-status-dashboard" style="padding: 8px 15px; border-top: 1px solid var(--border-color);"></div>`
		).appendTo(frm.layout.wrapper.find('.form-page'))
	}
	frm.cups_status_wrapper.html(html)
}

function refresh_cups_status_dashboard(frm) {
	if (frm.is_new() || !frm.doc.printer_name) {
		return
	}
	frappe.call({
		doc: frm.doc,
		method: 'get_cups_printer_status',
		callback(r) {
			render_cups_status_dashboard(frm, r.message || {})
		},
	})
}

function show_configure_dialog(frm) {
	frappe.call({
		doc: frm.doc,
		method: 'get_cups_printer_status',
		callback(r) {
			const status = r.message || {}
			const dialog = new frappe.ui.Dialog({
				title: __('Configure Printer'),
				fields: [
					{
						fieldname: 'device_uri',
						fieldtype: 'Data',
						label: __('Device URI'),
						default: frm.doc.device_uri,
					},
					{
						fieldname: 'ppdname',
						fieldtype: 'Autocomplete',
						label: __('Driver (PPD)'),
					},
					{
						fieldname: 'printer_location',
						fieldtype: 'Data',
						label: __('Printer Location'),
						default: frm.doc.printer_location,
						description: __('Physical location shown in CUPS and ERPNext, e.g. Chelsea Receiving Dock'),
					},
					{
						fieldname: 'enabled',
						fieldtype: 'Check',
						label: __('Enabled'),
						default: status.is_enabled ? 1 : 0,
					},
					{
						fieldname: 'accept_jobs',
						fieldtype: 'Check',
						label: __('Accepting Jobs'),
						default: status.is_accepting_jobs ? 1 : 0,
					},
				],
				primary_action_label: __('Save'),
				primary_action(values) {
					const ppd_options = dialog.fields_dict.ppdname._data || []
					const ppd_match = ppd_options.find(
						option => option.label === values.ppdname || option.value === values.ppdname
					)
					frappe.call({
						doc: frm.doc,
						method: 'configure_printer_queue',
						args: {
							device_uri: values.device_uri,
							ppdname: ppd_match ? ppd_match.value : values.ppdname,
							printer_location: values.printer_location,
							enabled: values.enabled ? 1 : 0,
							accept_jobs: values.accept_jobs ? 1 : 0,
						},
						freeze: true,
						callback() {
							dialog.hide()
							frm.reload_doc()
						},
					})
				},
			})
			dialog.show()
			load_ppds_for_dialog(frm.doc.server_ip, frm.doc.port, dialog.fields_dict.ppdname)
		},
	})
}

function show_printer_options_dialog(frm) {
	frappe.call({
		doc: frm.doc,
		method: 'get_printer_options',
		callback(r) {
			const payload = r.message || {}
			const options = payload.options || {}
			if (!Object.keys(options).length) {
				frappe.msgprint(payload.message || __('No printer options available for this queue.'))
				return
			}

			const common_names = [
				'media',
				'MediaSize',
				'PageSize',
				'sides',
				'Sides',
				'ColorModel',
				'print-quality',
				'PrintQuality',
			]
			const fields = []
			const seen = new Set()

			common_names.forEach(name => {
				if (!options[name]) {
					return
				}
				seen.add(name)
				fields.push({
					fieldname: name,
					fieldtype: 'Select',
					label: frappe.model.unscrub(name),
					options: options[name].choices.join('\n'),
					default: options[name].current,
				})
			})

			Object.keys(options)
				.sort()
				.forEach(name => {
					if (seen.has(name)) {
						return
					}
					fields.push({
						fieldname: name,
						fieldtype: 'Select',
						label: frappe.model.unscrub(name),
						options: options[name].choices.join('\n'),
						default: options[name].current,
					})
				})

			const dialog = new frappe.ui.Dialog({
				title: __('Printer Options'),
				fields,
				size: 'large',
				primary_action_label: __('Save'),
				primary_action(values) {
					const selected = {}
					Object.keys(options).forEach(name => {
						if (values[name]) {
							selected[name] = values[name]
						}
					})
					frappe.call({
						doc: frm.doc,
						method: 'set_printer_options',
						args: { options: selected },
						freeze: true,
						callback() {
							dialog.hide()
							frappe.show_alert({
								message: __('Printer options updated'),
								indicator: 'green',
							})
						},
					})
				},
			})
			dialog.show()
		},
	})
}

function delete_printer_from_cups(frm) {
	frappe.confirm(__('Delete {0} from CUPS and remove this record?', [frm.doc.printer_name]), () => {
		frappe.call({
			doc: frm.doc,
			method: 'delete_printer_queue',
			freeze: true,
			callback() {
				frappe.show_alert({
					message: __('Printer deleted'),
					indicator: 'green',
				})
				frappe.set_route('List', 'Network Printer Settings')
			},
		})
	})
}

function sync_from_cups(frm) {
	frappe.call({
		doc: frm.doc,
		method: 'sync_from_cups',
		freeze: true,
		callback() {
			frappe.show_alert({
				message: __('Synced printer details from CUPS'),
				indicator: 'green',
			})
			frm.reload_doc()
		},
	})
}

function print_test(frm) {
	frappe.call({
		doc: frm.doc,
		method: 'print_test_page',
		freeze: true,
		callback(r) {
			frappe.show_alert({
				message: r.message?.message || __('Test submitted'),
				indicator: 'green',
			})
		},
	})
}

function ping_printer(frm) {
	frappe.call({
		doc: frm.doc,
		method: 'ping_printer',
		freeze: true,
		callback(r) {
			const result = r.message || {}
			let indicator = 'orange'
			if (result.reachable === true) {
				indicator = 'green'
			} else if (result.reachable === false) {
				indicator = 'red'
			}

			const lines = [result.message]
			if (result.host) {
				lines.push(`${__('Host')}: ${frappe.utils.escape_html(result.host)}`)
			}
			if (result.device_uri) {
				lines.push(`${__('Device URI')}: ${frappe.utils.escape_html(result.device_uri)}`)
			}
			if (result.cups_location) {
				lines.push(`${__('CUPS Location')}: ${frappe.utils.escape_html(result.cups_location)}`)
			}
			if (result.make_model) {
				lines.push(`${__('Make / Model')}: ${frappe.utils.escape_html(result.make_model)}`)
			}

			frappe.msgprint({
				title: __('Printer Connectivity'),
				message: lines.join('<br>'),
				indicator,
			})
		},
	})
}

function pull_cups_printer_info(frm) {
	if (frm.is_new() || !frm.doc.printer_name) {
		return
	}
	frappe.call({
		doc: frm.doc,
		method: 'get_cups_printer_info',
		callback(r) {
			const info = r.message || {}
			if (!frm.doc.printer_location && info.printer_location) {
				frm.set_value('printer_location', info.printer_location)
			}
			if (!frm.doc.device_uri && info.device_uri) {
				frm.set_value('device_uri', info.device_uri)
			}
		},
	})
}

frappe.ui.form.on('Network Printer Settings', {
	refresh(frm) {
		if (!frm.is_new() && frappe.user.has_role('System Manager')) {
			frm.add_custom_button(__('Configure Printer'), () => show_configure_dialog(frm), __('Actions'))
			frm.add_custom_button(__('Sync from CUPS'), () => sync_from_cups(frm), __('Actions'))
			frm.add_custom_button(__('Print Test'), () => print_test(frm), __('Actions'))
			frm.add_custom_button(__('Ping Printer'), () => ping_printer(frm), __('Actions'))
			if (frm.doc.printer_type === 'General Purpose') {
				frm.add_custom_button(__('Printer Options'), () => show_printer_options_dialog(frm), __('Actions'))
			}
			frm.add_custom_button(__('Delete from CUPS'), () => delete_printer_from_cups(frm), __('Actions'))
		}
		if (!frm.is_new() && frm.doc.printer_name) {
			pull_cups_printer_info(frm)
			refresh_cups_status_dashboard(frm)
		}
	},
	after_save(frm) {
		printers_cache = []
		frm.trigger('connect_print_server')
		refresh_cups_status_dashboard(frm)
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
					if (frm.fields_dict.printer_name?.set_data) {
						frm.fields_dict.printer_name.set_data(printers_cache)
					}
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
			pending_printer_name = frm.doc.printer_name
			frm.trigger('connect_print_server')
			return
		}
		set_location_from_cache(frm, frm.doc.printer_name)
	},
})
