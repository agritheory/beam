// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.provide('frappe.ui.form')

frappe.ui.form.NetworkPrinterSettingsQuickEntryForm = class NetworkPrinterSettingsQuickEntryForm extends (
	frappe.ui.form.QuickEntryForm
) {
	constructor(doctype, after_insert, init_callback, doc, force) {
		super(doctype, after_insert, init_callback, doc, force)
		this.skip_redirect_on_error = true
		this.current_step = 0
		this.wizard_state = {
			server_ip: 'localhost',
			port: 631,
			action: 'create',
			kind: 'device',
			selection: null,
			device_uri: '',
			ppdname: '',
			use_manual_uri: false,
		}
		this.discovery_options = []
		this.ppd_options = []
	}

	render_dialog() {
		const me = this
		this.dialog = new frappe.ui.Dialog({
			title: __('Add Network Printer'),
			fields: this.get_all_fields(),
			size: 'large',
		})

		this.dialog.fields_dict.discovery.$input.on('awesomplete-selectcomplete', () => {
			me.on_discovery_select()
		})

		this.dialog.fields_dict.printer_type.$input.on('change', () => {
			me.set_default_ppd()
		})

		this.dialog.onhide = () => {
			me.dialog.fields_dict.discovery.$input.off('awesomplete-selectcomplete')
			me.dialog.fields_dict.printer_type.$input.off('change')
		}

		this.register_wizard_actions()
		this.dialog.show()
		this.show_step(0)
	}

	get_step_values(step) {
		const fieldnames = [
			['server_ip', 'port'],
			['discovery', 'use_manual_uri', 'device_uri'],
			['__newname', 'printer_name', 'printer_location', 'printer_type'],
			['ppdname'],
		][step]
		const values = {}
		;(fieldnames || []).forEach(fieldname => {
			values[fieldname] = this.dialog.get_value(fieldname)
		})
		return values
	}

	get_all_fields() {
		return [
			{
				fieldtype: 'Section Break',
				label: __('Print Server'),
				fieldname: 'step_server_section',
			},
			{
				fieldname: 'server_ip',
				fieldtype: 'Data',
				label: __('Server IP'),
				reqd: 1,
				default: 'localhost',
			},
			{
				fieldname: 'port',
				fieldtype: 'Int',
				label: __('Port'),
				reqd: 1,
				default: 631,
			},
			{
				fieldtype: 'Section Break',
				label: __('Discovery'),
				fieldname: 'step_discovery_section',
			},
			{
				fieldname: 'discovery',
				fieldtype: 'Autocomplete',
				label: __('Discovered Printer or Queue'),
			},
			{
				fieldname: 'use_manual_uri',
				fieldtype: 'Check',
				label: __('Enter device URI manually'),
			},
			{
				fieldname: 'device_uri',
				fieldtype: 'Data',
				label: __('Device URI'),
				depends_on: 'eval:doc.use_manual_uri',
			},
			{
				fieldtype: 'Section Break',
				label: __('Printer Details'),
				fieldname: 'step_details_section',
			},
			{
				fieldname: '__newname',
				fieldtype: 'Data',
				label: __('Network Printer Settings Name'),
			},
			{
				fieldname: 'printer_name',
				fieldtype: 'Data',
				label: __('CUPS Queue Name'),
			},
			{
				fieldname: 'printer_location',
				fieldtype: 'Data',
				label: __('Printer Location'),
				description: __('Physical location shown in CUPS, e.g. Chelsea Receiving Dock'),
			},
			{
				fieldname: 'printer_type',
				fieldtype: 'Select',
				label: __('Printer Type'),
				options: '\nGeneral Purpose\nLabel / RAW',
				default: 'Label / RAW',
			},
			{
				fieldtype: 'Section Break',
				label: __('Driver'),
				fieldname: 'step_driver_section',
			},
			{
				fieldname: 'ppdname',
				fieldtype: 'Autocomplete',
				label: __('Driver (PPD)'),
			},
		]
	}

	register_wizard_actions() {
		const me = this
		this.dialog.set_primary_action(__('Next'), () => me.next_step())
		this.dialog.set_secondary_action_label(__('Back'))
		this.dialog.set_secondary_action(() => me.prev_step())
		this.dialog.add_custom_action(__('Test Connection'), () => me.test_connection(), 'btn-test-connection')
		this.test_connection_btn = this.dialog.custom_actions.find('.btn-test-connection')
		this.test_connection_btn.hide()
	}

	show_test_connection_button(step) {
		if (!this.test_connection_btn) {
			return
		}
		if (step === 1 || step === 2) {
			this.test_connection_btn.show()
		} else {
			this.test_connection_btn.hide()
		}
	}

	get_current_device_uri() {
		const values = this.get_step_values(1)
		if (values.use_manual_uri) {
			return values.device_uri
		}
		if (this.wizard_state.device_uri) {
			return this.wizard_state.device_uri
		}
		if (this.wizard_state.selection) {
			return this.wizard_state.selection.device_uri || this.wizard_state.selection.value
		}
		return values.device_uri
	}

	test_connection() {
		const device_uri = this.get_current_device_uri()
		if (!device_uri) {
			frappe.msgprint(__('Select a discovered printer or enter a device URI first.'))
			return
		}
		frappe
			.call({
				method: 'beam.beam.overrides.network_printer_settings.test_device_uri',
				args: { device_uri },
				freeze: true,
			})
			.then(r => {
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
				if (result.port) {
					lines.push(`${__('Port')}: ${result.port}`)
				}
				;(result.warnings || []).forEach(warning => {
					lines.push(frappe.utils.escape_html(warning))
				})
				frappe.msgprint({
					title: __('Printer Connectivity'),
					message: lines.join('<br>'),
					indicator,
				})
			})
	}

	show_step(step) {
		this.current_step = step
		const sections = [
			['server_ip', 'port'],
			['discovery', 'use_manual_uri', 'device_uri'],
			['__newname', 'printer_name', 'printer_location', 'printer_type'],
			['ppdname'],
		]
		const all_fields = sections.flat()
		all_fields.forEach(fieldname => {
			this.dialog.get_field(fieldname)?.$wrapper?.hide()
		})
		;(sections[step] || []).forEach(fieldname => {
			this.dialog.get_field(fieldname)?.$wrapper?.show()
		})

		if (step === 3 && this.wizard_state.action === 'link') {
			this.finish_wizard()
			return
		}

		if (step === 0) {
			this.dialog.get_primary_btn().text(__('Next'))
		} else if (step === 3) {
			this.dialog.get_primary_btn().text(__('Create Printer'))
		} else if (step === 2 && this.wizard_state.action === 'link') {
			this.dialog.get_primary_btn().text(__('Link Printer'))
		} else {
			this.dialog.get_primary_btn().text(__('Next'))
		}
		this.show_test_connection_button(step)
	}

	next_step() {
		if (this.current_step === 0) {
			const values = this.get_step_values(0)
			if (!values.server_ip || !values.port) {
				frappe.msgprint(__('Server IP and Port are required.'))
				return
			}
			this.wizard_state.server_ip = values.server_ip
			this.wizard_state.port = values.port
			this.load_discovery_options().then(() => this.show_step(1))
			return
		}
		if (this.current_step === 1) {
			if (!this.prepare_discovery_step(this.get_step_values(1))) {
				return
			}
			this.show_step(2)
			return
		}
		if (this.current_step === 2) {
			const values = this.get_step_values(2)
			if (!values.__newname || !values.printer_name) {
				frappe.msgprint(__('Network Printer Settings Name and CUPS Queue Name are required.'))
				return
			}
			if (this.wizard_state.action === 'link') {
				this.finish_wizard()
				return
			}
			this.load_ppd_options().then(() => {
				this.set_default_ppd()
				this.show_step(3)
			})
			return
		}
		if (this.current_step === 3) {
			this.finish_wizard()
		}
	}

	prev_step() {
		if (this.current_step === 0) {
			return
		}
		if (this.current_step === 2 && this.wizard_state.action === 'link') {
			this.show_step(1)
			return
		}
		this.show_step(this.current_step - 1)
	}

	load_discovery_options() {
		const me = this
		const server_ip = this.dialog.get_value('server_ip') || this.wizard_state.server_ip
		const port = this.dialog.get_value('port') || this.wizard_state.port
		return frappe
			.call({
				method: 'beam.beam.overrides.network_printer_settings.get_wizard_devices',
				args: { server_ip, port },
				freeze: true,
			})
			.then(r => {
				me.discovery_options = r.message || []
				me.dialog.fields_dict.discovery.set_data(me.discovery_options)
			})
	}

	load_ppd_options() {
		const me = this
		return frappe
			.call({
				method: 'beam.beam.overrides.network_printer_settings.get_ppds',
				args: {
					server_ip: this.wizard_state.server_ip,
					port: this.wizard_state.port,
				},
				freeze: true,
			})
			.then(r => {
				me.ppd_options = r.message || []
				me.dialog.fields_dict.ppdname.set_data(me.ppd_options)
			})
	}

	on_discovery_select() {
		const label = this.dialog.get_value('discovery')
		const match = this.discovery_options.find(option => option.label === label || option.value === label)
		if (!match) {
			return
		}
		this.wizard_state.selection = match
		this.wizard_state.kind = match.kind
		if (match.kind === 'queue') {
			this.wizard_state.action = match.configured ? 'block' : 'link'
			this.dialog.set_value('printer_name', match.value)
			this.dialog.set_value('printer_location', match.location || '')
			this.dialog.set_value('device_uri', match.device_uri || '')
		} else {
			this.wizard_state.action = 'create'
			this.dialog.set_value('device_uri', match.device_uri || match.value)
			const suggested = (match.device_uri || match.value).split('/').pop() || ''
			if (suggested && !this.dialog.get_value('printer_name')) {
				this.dialog.set_value('printer_name', suggested.replace(/[^a-zA-Z0-9_-]/g, '_'))
			}
		}
	}

	prepare_discovery_step(values) {
		if (values.use_manual_uri) {
			if (!values.device_uri) {
				frappe.msgprint(__('Device URI is required.'))
				return false
			}
			if (values.device_uri.startsWith('usb://')) {
				frappe.msgprint(__('USB printers are not supported.'))
				return false
			}
			this.wizard_state.action = 'create'
			this.wizard_state.kind = 'device'
			this.wizard_state.device_uri = values.device_uri
			this.wizard_state.selection = null
			return true
		}

		if (!this.wizard_state.selection) {
			this.on_discovery_select()
		}
		if (!this.wizard_state.selection) {
			frappe.msgprint(__('Select a discovered printer or queue, or enter a URI manually.'))
			return false
		}
		if (this.wizard_state.selection.configured) {
			frappe.msgprint(
				__('This printer is already configured as {0}.', [
					this.wizard_state.selection.nps_name || this.wizard_state.selection.label,
				])
			)
			return false
		}
		if (this.wizard_state.kind === 'queue') {
			this.wizard_state.action = 'link'
			this.wizard_state.device_uri = this.wizard_state.selection.device_uri || ''
		} else {
			this.wizard_state.action = 'create'
			this.wizard_state.device_uri = this.wizard_state.selection.device_uri || this.wizard_state.selection.value
		}
		return true
	}

	set_default_ppd() {
		const printer_type = this.dialog.get_value('printer_type')
		const default_ppd = printer_type === 'General Purpose' ? 'everywhere' : 'raw'
		const match = this.ppd_options.find(option => option.value === default_ppd)
		if (match) {
			this.dialog.set_value('ppdname', match.label)
			this.wizard_state.ppdname = match.value
		}
	}

	get_ppd_value() {
		const label = this.dialog.get_value('ppdname')
		const match = this.ppd_options.find(option => option.label === label || option.value === label)
		return match ? match.value : label
	}

	finish_wizard() {
		const details = this.get_step_values(2)
		const driver = this.get_step_values(3)
		if (!details.__newname || !details.printer_name) {
			frappe.msgprint(__('Network Printer Settings Name and CUPS Queue Name are required.'))
			return
		}
		const common_args = {
			name: details.__newname,
			server_ip: this.wizard_state.server_ip,
			port: this.wizard_state.port,
			printer_name: details.printer_name,
			printer_location: details.printer_location || '',
			printer_type: details.printer_type || '',
		}

		if (this.wizard_state.action === 'link') {
			frappe
				.call({
					method: 'beam.beam.overrides.network_printer_settings.link_existing_printer',
					args: common_args,
					freeze: true,
				})
				.then(r => this.on_wizard_complete(r.message))
			return
		}

		frappe
			.call({
				method: 'beam.beam.overrides.network_printer_settings.create_printer_queue',
				args: {
					...common_args,
					device_uri: this.wizard_state.device_uri || this.dialog.get_value('device_uri'),
					ppdname: this.get_ppd_value() || driver.ppdname,
				},
				freeze: true,
			})
			.then(r => this.on_wizard_complete(r.message))
	}

	on_wizard_complete(doc) {
		this.dialog.hide()
		frappe.show_alert({
			message: __('Printer {0} configured', [doc.name]),
			indicator: 'green',
		})
		if (this.after_insert) {
			this.after_insert(doc)
		} else {
			frappe.set_route('Form', 'Network Printer Settings', doc.name)
		}
	}

	insert() {
		return Promise.resolve()
	}
}
