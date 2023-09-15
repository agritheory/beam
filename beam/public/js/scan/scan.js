import onScan from 'onscan.js'

function waitForElement(selector) {
	return new Promise(resolve => {
		if (document.querySelector(selector)) {
			return resolve(document.querySelector(selector))
		}
		const observer = new MutationObserver(mutations => {
			if (document.querySelector(selector)) {
				resolve(document.querySelector(selector))
				observer.disconnect()
			}
		})
		observer.observe(document.body, {
			childList: true,
			subtree: true,
		})
	})
}

waitForElement('[data-route]').then(element => {
	let observer = new MutationObserver(() => {
		new ScanHandler()
	})
	const config = { attributes: true, childList: false, characterData: true }
	observer.observe(element, config)
})

class ScanHandler {
	constructor() {
		let me = this
		if (
			!window.hasOwnProperty('scanHandler') ||
			!window.scanHandler.hasOwnProperty('scanner') ||
			!window.scanHandler.scanner.isAttachedTo(document)
		) {
			me.scanner = onScan.attachTo(document, {
				onScan: async function (sCode, iQty) {
					await me.get_scanned_context(sCode, iQty)
				},
				ignoreIfFocusOn: '.frappe-input',
			})
			window.scanHandler = me
		}
	}
	reduceContext() {
		if (!frappe.boot.beam_doctypes) {
			frappe.xcall('beam.beam.scan.config.get_scan_doctypes').then(r => {
				frappe.boot.beam = r
			})
		}
		const route = frappe.get_route()
		if (route[0] == 'List' && frappe.boot.beam.listview.includes(route[1])) {
			return {
				listview: route[1],
			}
		} else if (route[0] == 'Form' && frappe.boot.beam.frm.includes(route[1])) {
			return {
				frm: route[1],
				doc: cur_frm.doc,
			}
		}
	}
	async get_scanned_context(sCode, iQty) {
		return new Promise(resolve => {
			const context = this.reduceContext()
			frappe.xcall('beam.beam.scan.scan', { barcode: sCode, context: context, current_qty: iQty }).then(r => {
				if (r && r.length) {
					if (Object.keys(frappe.boot.beam.client).includes(r[0].action)) {
						let path = frappe.boot.beam.client[r[0].action][0]
						resolve(path.split('.').reduce((o, i) => o[i], window)(r)) // calls (first) custom built callback registered in hooks
					} else {
						resolve(this[String(r[0].action)](r)) // TODO: this only calls the first function
					}
				}
				// TODO: else error
			})
		})
	}
	route(barcode_context) {
		frappe.set_route('Form', barcode_context[0].field, barcode_context[0].target)
	}
	filter(barcode_context) {
		const filters_to_apply = barcode_context.map(filterset => {
			window.fltr.add_filter(filterset.doctype, filterset.field, '=', filterset.target)
		})
		Promise.all(filters_to_apply).then(() => {
			window.fltr.apply()
		})
	}
	add_or_associate(barcode_context) {
		if (barcode_context.length < 1) {
			return
		}
		barcode_context.forEach(field => {
			if (
				!cur_frm.doc.items.some(row => {
					if (
						cur_frm.doc.doctype == 'Stock Entry' &&
						[
							'Send to Subcontractor',
							'Material Transfer for Manufacture',
							'Material Transfer',
							'Material Receipt',
							'Manufacture',
						].includes(cur_frm.doc.stock_entry_type)
					) {
						return row.item_code == field.context.item_code || row.handling_unit
					}
					return (
						(row.item_code == field.context.item_code && row.stock_qty == field.context.stock_qty) ||
						row.handling_unit == field.context.handling_unit
					)
				})
			) {
				if (!cur_frm.doc.items.length || !cur_frm.doc.items[0].item_code) {
					cur_frm.doc.items = []
				}
				let child = cur_frm.add_child('items', field.context)
				if (cur_frm.doc.doctype == 'Stock Entry') {
					frappe.model.set_value(child.doctype, child.name, 's_warehouse', field.context.warehouse)
				}
			} else {
				for (let row of cur_frm.doc.items) {
					if (
						cur_frm.doc.doctype == 'Stock Entry' &&
						[
							'Send to Subcontractor',
							'Material Transfer for Manufacture',
							'Material Transfer',
							'Material Receipt',
							'Manufacture',
						].includes(cur_frm.doc.stock_entry_type) &&
						row.item_code == field.context.item_code &&
						!row.handling_unit
					) {
						frappe.model.set_value(row.doctype, row.name, field.field, field.target)
						continue
					}
					if (
						(row.item_code == field.context.item_code && row.stock_qty == field.context.stock_qty) ||
						row.handling_unit == field.context.handling_unit
					) {
						if (cur_frm.doc.doctype == 'Stock Entry') {
							if ((field.field = 'basic_rate')) {
								cur_frm.events.set_basic_rate(cur_frm, row.doctype, row.name)
							} else {
								frappe.model.set_value(row.doctype, row.name, field.field, field.target)
							}
						}
					}
				}
			}
		})
		cur_frm.refresh_field('items')
	}
	set_warehouse(barcode_context) {
		if (barcode_context.length > 0) {
			barcode_context = barcode_context[0]
		} else {
			return
		}
		const source_warehouses = ['Material Consumption for Manufacture', 'Material Issue']
		const target_warehouses = ['Material Receipt', 'Manufacture']
		const both_warehouses = [
			'Material Transfer for Manufacture',
			'Material Transfer',
			'Send to Subcontractor',
			'Repack',
		]
		if (barcode_context.doctype == 'Stock Entry' && source_warehouses.includes(cur_frm.doc.stock_entry_type)) {
			cur_frm.set_value('from_warehouse', barcode_context.target)
			for (let row of cur_frm.doc.items) {
				frappe.model.set_value(row.doctype, row.name, 's_warehouse', barcode_context.target)
			}
		} else if (barcode_context.doctype == 'Stock Entry' && target_warehouses.includes(cur_frm.doc.stock_entry_type)) {
			cur_frm.set_value('to_warehouse', barcode_context.target)
			for (let row of cur_frm.doc.items) {
				frappe.model.set_value(row.doctype, row.name, 't_warehouse', barcode_context.target)
			}
		} else if (barcode_context.doctype == 'Stock Entry' && both_warehouses.includes(cur_frm.doc.stock_entry_type)) {
			cur_frm.set_value('from_warehouse', barcode_context.target)
			cur_frm.set_value('to_warehouse', barcode_context.target)
			for (let row of cur_frm.doc.items) {
				frappe.model.set_value(row.doctype, row.name, 's_warehouse', barcode_context.target)
				frappe.model.set_value(row.doctype, row.name, 't_warehouse', barcode_context.target)
			}
		}
	}
	add_or_increment(barcode_context) {
		if (barcode_context.length > 0) {
			barcode_context = barcode_context[0]
		} else {
			return
		}
		// if not item code, add row
		// else find last row with item code and increment
		if (
			!cur_frm.doc.items.some(row => {
				return (
					(row.item_code == barcode_context.context.item_code && !row.handling_unit) ||
					row.barcode == barcode_context.context.barcode
				)
			})
		) {
			if (!cur_frm.doc.items.length || !cur_frm.doc.items[0].item_code) {
				cur_frm.doc.items = []
			}
			const row = cur_frm.add_child('items', barcode_context.context)
			// a first-time scan of an item in Stock Entry does not automatically set the rate, so run it manually
			if (cur_frm.doc.doctype == 'Stock Entry') {
				cur_frm.events.set_basic_rate(cur_frm, row.doctype, row.name)
			}
		} else {
			for (let row of cur_frm.doc.items) {
				if (
					(row.item_code == barcode_context.context.item_code && !row.handling_unit) ||
					row.barcode == barcode_context.context.barcode
				) {
					frappe.model.set_value(row.doctype, row.name, 'qty', row.qty + 1)
				}
			}
		}
		cur_frm.refresh_field('items')
	}
	set_item_code_and_handling_unit(barcode_context) {
		barcode_context.forEach(action => {
			cur_frm.set_value(action.field, action.target)
		})
	}
}
