// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Receipt', {
	async refresh(frm) {
		await setup_scale(frm)
	},
})

// Global scale state
const scaleState = {
	device: null,
	frm: null,
	connected: false,
	config: null,
	activeRowIdx: null,
	workflowState: 'IDLE',
	weightValue: 0,
	weightUnit: 'oz',
	statusCode: 0,
	reportCount: 0,
	massUoms: [],
	conversionFactors: {},
	overlay: null,
	sidebarWidget: null,
	handlersBound: false,
	lastReadingKey: null,
	stableReadingCount: 0,
	qtyFilled: false,
	lastStatusText: '',
}

async function setup_scale(frm) {
	if (frm.doc.docstatus) return

	// Always update frm reference so the active form is current
	scaleState.frm = frm
	scaleState.massUoms = frappe.boot.beam.mass_uoms || []
	scaleState.config = (frappe.boot.beam.scale_configs || {})[frm.doctype]

	if (!scaleState.config) return

	ensureSidebarWidget(frm)
	ensureScalePopover()

	// If already connected, restore visible state without re-opening device
	if (scaleState.connected) {
		updateConnectionStatus()
		scaleState.overlay.style.display = 'block'
		updateRowHighlight()
	}
}

function ensureSidebarWidget(frm) {
	// Remove any stale widget left by a previous frm render
	document.querySelectorAll('#scale-sidebar-widget').forEach(el => el.remove())

	const wrapper = document.createElement('div')
	wrapper.id = 'scale-sidebar-widget'
	wrapper.innerHTML = `
		<div style="padding: 12px; background: var(--bg-light); border-radius: 4px; border: 1px solid var(--border-color); font-size: 12px; text-align: center;">
			<div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
				<span id="scale-connection-dot" style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #ccc;"></span>
				<span id="scale-connection-text">Not connected</span>
			</div>
			<button id="use-scale-btn" class="btn btn-sm btn-primary" style="width: 100%;">USE SCALE</button>
			<details style="margin-top: 8px; font-size: 11px;">
				<summary style="cursor: pointer; color: var(--text-muted);">Raw HID</summary>
				<code id="scale-raw-hex" style="display: block; margin-top: 4px; word-break: break-all; color: var(--text-muted);">—</code>
			</details>
		</div>
	`

	const $sidebar = frm.sidebar && frm.sidebar.sidebar
	if ($sidebar && $sidebar.length) {
		$sidebar.prepend(wrapper)
		scaleState.sidebarWidget = wrapper
	}

	document.getElementById('use-scale-btn').addEventListener('click', () => {
		use_scale(frm)
	})
}

function ensureScalePopover() {
	// Reuse existing popover across form navigations
	const existing = document.getElementById('scale-row-popover')
	if (existing) {
		scaleState.overlay = existing
		return
	}

	const popover = document.createElement('div')
	popover.id = 'scale-row-popover'
	popover.style.cssText = `
		position: fixed;
		right: 24px;
		top: 100px;
		width: 240px;
		background: var(--card-bg);
		border: 1px solid var(--border-color);
		border-left: 4px solid var(--primary-color);
		border-radius: 6px;
		padding: 16px;
		box-shadow: 0 2px 8px rgba(0,0,0,0.1);
		z-index: 2000;
		transition: top 200ms ease;
		display: none;
		font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
	`
	popover.innerHTML = `
		<div id="scale-popover-header" style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
			<span id="scale-item-name">—</span> <span id="scale-row-progress">[—]</span>
		</div>
		<div style="text-align: center; margin-bottom: 8px; line-height: 1;">
			<span id="scale-readout-value" style="font-size: 72px; font-weight: bold; color: var(--text-color); font-family: 'Monaco', 'Courier', monospace; white-space: nowrap;">—</span>
			<span id="scale-readout-unit" style="font-size: 36px; font-weight: bold; color: var(--text-muted); font-family: 'Monaco', 'Courier', monospace; margin-left: 4px;"></span>
		</div>
		<div id="scale-readout-converted" style="font-size: 36px; font-weight: 600; text-align: center; margin-bottom: 12px; color: var(--primary-color); font-family: 'Monaco', 'Courier', monospace; min-height: 1.2em;">—</div>
		<div id="scale-status-text" style="font-size: 12px; color: var(--text-muted); text-align: center;">—</div>
	`
	document.body.appendChild(popover)
	scaleState.overlay = popover
}

async function use_scale(frm) {
	// Already open — just show the popover and update state
	if (scaleState.connected && scaleState.device) {
		updateConnectionStatus()
		scaleState.overlay.style.display = 'block'
		document.getElementById('use-scale-btn').style.display = 'none'
		updateRowHighlight()
		return
	}

	const btn = document.getElementById('use-scale-btn')
	btn.disabled = true
	btn.innerHTML = 'Connecting...'

	try {
		const devices = await navigator.hid.requestDevice({
			filters: [{ vendorId: 0x1446 }, { vendorId: 0x11ff }],
		})

		if (devices.length === 0) {
			frappe.msgprint('No scale device selected')
			btn.disabled = false
			btn.innerHTML = 'USE SCALE'
			return
		}

		scaleState.device = devices[0]
		await scaleState.device.open()
		scaleState.connected = true
		scaleState.workflowState = 'WAITING'
		scaleState.activeRowIdx = 0

		await loadConversionFactors(frm)

		updateConnectionStatus()
		updateRowHighlight()
		btn.style.display = 'none'
		scaleState.overlay.style.display = 'block'

		if (!scaleState.handlersBound) {
			bindScaleInputHandler()
			scaleState.handlersBound = true
		}
	} catch (error) {
		console.error('Scale connection failed:', error)
		frappe.msgprint(`Scale connection failed: ${error.message}`)
		btn.disabled = false
		btn.innerHTML = 'USE SCALE'
	}
}

function bindScaleInputHandler() {
	scaleState.device.oninputreport = report => {
		scaleState.reportCount++
		const parsed = parseScaleData(report.data)
		const readingKey = `${parsed.raw}:${parsed.status}`

		if (readingKey === scaleState.lastReadingKey) {
			return
		}
		scaleState.lastReadingKey = readingKey

		scaleState.weightValue = parsed.value
		scaleState.weightUnit = parsed.unit
		scaleState.statusCode = parsed.status
		scaleState.lastRawHex = rawBytesToHex(report.data)

		handleWorkflowState(parsed)
		updatePopover()
		updateSidebarWidget()
	}
}

function parseScaleData(data) {
	const status = data.getUint8(0)
	const unitCode = data.getUint8(1)
	const exponent = data.getInt8(2)
	const raw = data.getUint16(3, true)
	const value = raw * Math.pow(10, exponent)

	const unit = unitCode === 11 ? 'oz' : unitCode === 12 ? 'lb' : unitCode === 2 ? 'g' : 'units'

	return { value, unit, status, raw, exponent }
}

function rawBytesToHex(data) {
	return Array.from(data)
		.map(b => b.toString(16).padStart(2, '0').toUpperCase())
		.join(' ')
}

function updateConnectionStatus() {
	const dot = document.getElementById('scale-connection-dot')
	const text = document.getElementById('scale-connection-text')
	if (scaleState.connected) {
		dot.style.background = '#4CAF50'
		text.textContent = 'Connected'
	} else {
		dot.style.background = '#ccc'
		text.textContent = 'Not connected'
	}
}

function updateSidebarWidget() {
	const rawHex = document.getElementById('scale-raw-hex')
	if (rawHex) {
		rawHex.textContent = scaleState.lastRawHex || '—'
	}
}

function updatePopover() {
	if (!scaleState.overlay) return

	const isStable = scaleState.statusCode === 4

	const valueEl = document.getElementById('scale-readout-value')
	const unitEl = document.getElementById('scale-readout-unit')
	if (isStable) {
		valueEl.textContent = scaleState.weightValue.toFixed(1)
		unitEl.textContent = scaleState.weightUnit
	} else {
		valueEl.textContent = '…'
		unitEl.textContent = ''
	}

	if (scaleState.activeRowIdx !== null) {
		const itemsTableField = scaleState.config.items_table_field || 'items'
		const items = scaleState.frm.doc[itemsTableField]

		if (items && items[scaleState.activeRowIdx]) {
			const row = items[scaleState.activeRowIdx]
			const itemName = row.item_name || row.item_code || '?'
			const rowNum = scaleState.activeRowIdx + 1
			const totalRows = items.length

			document.getElementById('scale-item-name').textContent = itemName
			document.getElementById('scale-row-progress').textContent = `[${rowNum}/${totalRows}]`

			const rowUom = row.uom || ''
			if (isStable && scaleState.massUoms.includes(rowUom)) {
				const converted = convertWeight(scaleState.weightValue, scaleState.weightUnit, rowUom)
				document.getElementById('scale-readout-converted').textContent = converted
			} else {
				document.getElementById('scale-readout-converted').textContent = ''
			}
		}
	}

	document.getElementById('scale-status-text').textContent = scaleState.lastStatusText
	updateRowHighlight()
}

function formatWeight(value, unit) {
	if (value === 0 || value < 0) {
		return '0 ' + unit
	}

	if (unit === 'oz') {
		const lbs = Math.floor(value / 16)
		const oz = value % 16
		if (lbs > 0) {
			return `${lbs.toFixed(0)} lb ${oz.toFixed(1)} oz`
		}
	}

	return `${value.toFixed(1)} ${unit}`
}

async function loadConversionFactors(frm) {
	const itemsTableField = scaleState.config.items_table_field || 'items'
	const items = frm.doc[itemsTableField] || []
	const uoms = [...new Set(items.map(r => r.uom).filter(u => scaleState.massUoms.includes(u)))]

	for (const toUom of uoms) {
		if (scaleState.conversionFactors[toUom] !== undefined) continue
		// Try Ounce → toUom, then Pound → toUom
		for (const fromUom of ['Ounce', 'Pound']) {
			const result = await frappe.db.get_value('UOM Conversion Factor', { from_uom: fromUom, to_uom: toUom }, 'value')
			if (result && result.message && result.message.value) {
				scaleState.conversionFactors[toUom] = { value: result.message.value, from: fromUom }
				break
			}
		}
		// Fall back: try inverse (toUom → Ounce)
		if (scaleState.conversionFactors[toUom] === undefined) {
			const result = await frappe.db.get_value('UOM Conversion Factor', { from_uom: toUom, to_uom: 'Ounce' }, 'value')
			if (result && result.message && result.message.value) {
				scaleState.conversionFactors[toUom] = { value: 1 / result.message.value, from: 'Ounce' }
			}
		}
	}
}

function convertWeight(value, fromUnit, toUom) {
	if (!scaleState.massUoms.includes(toUom)) return ''

	const entry = scaleState.conversionFactors[toUom]
	if (!entry) return ''

	// Convert value to the same "from" unit the factor uses
	let inOz = fromUnit === 'oz' ? value : value * 16
	let inFrom = entry.from === 'Ounce' ? inOz : inOz / 16

	const converted = inFrom * entry.value
	return `${converted.toFixed(3)} ${toUom}`
}

function handleWorkflowState(parsed) {
	const isStable = parsed.status === 4
	const zeroThreshold = scaleState.config.zero_threshold || 0.1
	const isZero = parsed.value < zeroThreshold
	const itemsTableField = scaleState.config.items_table_field || 'items'
	const items = scaleState.frm.doc[itemsTableField]

	if (!items || items.length === 0) {
		scaleState.workflowState = 'IDLE'
		scaleState.lastStatusText = 'No items to weigh'
		return
	}

	if (scaleState.activeRowIdx === null) {
		scaleState.activeRowIdx = 0
	}

	switch (scaleState.workflowState) {
		case 'IDLE':
			scaleState.workflowState = 'WAITING'
			scaleState.lastStatusText = 'Place item on scale'
			break

		case 'WAITING':
			if (isStable && !isZero) {
				scaleState.workflowState = 'STABLE'
				scaleState.stableReadingCount = 1
				scaleState.lastStatusText = 'Stable'
			} else {
				scaleState.lastStatusText = 'Place item on scale'
			}
			break

		case 'STABLE':
			if (isStable && !isZero) {
				scaleState.stableReadingCount++
				if (scaleState.stableReadingCount >= 2) {
					scaleState.workflowState = 'FILL_QTY'
					fillQtyFromWeight()
				} else {
					scaleState.lastStatusText = `Stable (${scaleState.stableReadingCount}/2)`
				}
			} else {
				scaleState.workflowState = 'WAITING'
				scaleState.lastStatusText = 'Place item on scale'
			}
			break

		case 'FILL_QTY':
			if (!scaleState.qtyFilled) {
				scaleState.qtyFilled = true
			}
			scaleState.workflowState = 'WAITING_FOR_ZERO'
			scaleState.lastStatusText = 'Remove item'
			break

		case 'WAITING_FOR_ZERO':
			if (isZero) {
				scaleState.workflowState = 'ZERO_DETECTED'
				scaleState.lastStatusText = 'Ready for next'
			} else {
				scaleState.lastStatusText = 'Remove item'
			}
			break

		case 'ZERO_DETECTED':
			if (scaleState.config.autoadvance_on_zero) {
				advanceToNextRow()
			} else {
				scaleState.lastStatusText = 'Ready for next'
			}
			break
	}
}

function fillQtyFromWeight() {
	if (scaleState.activeRowIdx === null) return

	const itemsTableField = scaleState.config.items_table_field || 'items'
	const qtyField = scaleState.config.qty_field || 'qty'
	const items = scaleState.frm.doc[itemsTableField]

	if (!items || !items[scaleState.activeRowIdx]) return

	const row = items[scaleState.activeRowIdx]
	const uomField = scaleState.config.uom_field || 'uom'
	const uom = row[uomField]

	let qtyToSet = scaleState.weightValue

	if (scaleState.massUoms.includes(uom)) {
		const entry = scaleState.conversionFactors[uom]
		if (entry) {
			let inOz = scaleState.weightUnit === 'oz' ? scaleState.weightValue : scaleState.weightValue * 16
			let inFrom = entry.from === 'Ounce' ? inOz : inOz / 16
			qtyToSet = inFrom * entry.value
		}
	}

	frappe.model.set_value(row.doctype, row.name, qtyField, qtyToSet)
	scaleState.lastStatusText = `Set qty: ${qtyToSet.toFixed(3)}`
}

function advanceToNextRow() {
	const itemsTableField = scaleState.config.items_table_field || 'items'
	const items = scaleState.frm.doc[itemsTableField]

	if (!items) return

	scaleState.activeRowIdx = (scaleState.activeRowIdx + 1) % items.length

	if (scaleState.activeRowIdx === 0) {
		scaleState.lastStatusText = 'All items done'
	} else {
		scaleState.workflowState = 'WAITING'
		scaleState.stableReadingCount = 0
		scaleState.qtyFilled = false
		scaleState.lastStatusText = 'Place item on scale'
	}

	updateRowHighlight()
}

function updateRowHighlight() {
	const itemsTableField = scaleState.config.items_table_field || 'items'
	const field = scaleState.frm.get_field(itemsTableField)

	if (!field || !field.grid) return

	const gridRows = field.grid.grid_rows || []

	gridRows.forEach((row, idx) => {
		if (!row.wrapper) return
		// row.wrapper is a jQuery object
		if (idx === scaleState.activeRowIdx) {
			row.wrapper.addClass('scale-row-active')
		} else {
			row.wrapper.removeClass('scale-row-active')
		}
	})

	if (scaleState.overlay && scaleState.activeRowIdx !== null && gridRows[scaleState.activeRowIdx]) {
		const activeWrapper = gridRows[scaleState.activeRowIdx].wrapper
		if (activeWrapper && activeWrapper.length) {
			// rect.top is already in viewport coordinates for position:fixed
			const rect = activeWrapper[0].getBoundingClientRect()
			scaleState.overlay.style.top = `${Math.max(8, rect.top)}px`
		}
	}
}

frappe.dom.set_style(`
	.scale-row-active {
		background: var(--yellow-highlight-color) !important;
		outline: 2px solid var(--yellow-100) !important;
	}
`)
