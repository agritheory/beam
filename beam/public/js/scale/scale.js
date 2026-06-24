// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Receipt', {
	async refresh(frm) {
		await setup_scale(frm)
	},
	items_add(frm, cdt, cdn) {
		if (!scaleState.connected) return

		const itemsTableField = (scaleState.config && scaleState.config.items_table_field) || 'items'
		const items = frm.doc[itemsTableField] || []
		const newRowIdx = items.findIndex(r => r.name === cdn)
		if (newRowIdx < 0) return

		focusScaleRow(newRowIdx)
	},
})

function resetScaleIterator() {
	scaleState.activeRowIdx = 0
	scaleState.workflowState = 'WAITING'
	scaleState.stableReadingCount = 0
	scaleState.qtyFilled = false
	scaleState.lastStatusText = 'Place item on scale'
	scaleState.lastReadingKey = null
}

function focusScaleRow(rowIdx) {
	scaleState.activeRowIdx = rowIdx
	scaleState.workflowState = 'WAITING'
	scaleState.stableReadingCount = 0
	scaleState.qtyFilled = false
	scaleState.lastStatusText = 'Place item on scale'
	scaleState.lastReadingKey = null
	updatePopover()
	updateRowHighlight()
}

// Global scale state
const scaleState = {
	device: null,
	frm: null,
	lastDocKey: null,
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
	rowFocusFrm: null,
	positionListenersBound: false,
	popoverResizeObserver: null,
	lastReadingKey: null,
	stableReadingCount: 0,
	qtyFilled: false,
	lastStatusText: '',
}

async function setup_scale(frm) {
	if (frm.doc.docstatus) return

	const docKey = `${frm.doctype}:${frm.doc.name}`
	const docChanged = scaleState.lastDocKey !== null && scaleState.lastDocKey !== docKey

	// Always update frm reference so the active form is current
	scaleState.frm = frm
	scaleState.lastDocKey = docKey
	scaleState.massUoms = frappe.boot.beam.mass_uoms || []
	scaleState.config = (frappe.boot.beam.scale_configs || {})[frm.doctype]

	if (!scaleState.config) return

	if (docChanged && scaleState.connected) {
		resetScaleIterator()
		loadConversionFactors(frm)
	}

	ensureSidebarWidget(frm)
	ensureScalePopover()
	bindScaleRowFocus(frm)

	// If already connected, restore visible state without re-opening device
	if (scaleState.connected) {
		updateConnectionStatus()
		scaleState.overlay.style.display = 'block'
		updatePopover()
		updateRowHighlight()
	}
}

function bindScaleRowFocus(frm) {
	if (scaleState.rowFocusFrm === frm) return

	if (scaleState.rowFocusFrm) {
		$(scaleState.rowFocusFrm.wrapper).off('.scale')
	}
	scaleState.rowFocusFrm = frm

	$(frm.wrapper).on('focusin.scale click.scale', function (e) {
		if (!scaleState.connected || !scaleState.config) return
		if (scaleState.frm !== frm) return

		const itemsTableField = scaleState.config.items_table_field || 'items'
		const field = frm.get_field(itemsTableField)
		if (!field || !field.grid) return

		const $target = $(e.target)
		if (!$target.closest(field.grid.wrapper).length) return
		if ($target.hasClass('grid-row-check')) return

		const $gridRow = $target.closest('.grid-row')
		if (!$gridRow.length) return

		const gridRow = $gridRow.data('grid_row')
		if (!gridRow || !gridRow.doc) return

		const items = frm.doc[itemsTableField] || []
		const rowIdx = items.findIndex(r => r.name === gridRow.doc.name)
		if (rowIdx < 0 || rowIdx === scaleState.activeRowIdx) return

		focusScaleRow(rowIdx)
	})
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
	const existing = document.getElementById('scale-row-popover')
	if (existing && existing.querySelector('.scale-popover-caret') && existing.querySelector('.scale-popover-bridge')) {
		scaleState.overlay = existing
		bindScalePopoverPositionListeners()
		return
	}
	if (existing) {
		existing.remove()
	}

	const popover = document.createElement('div')
	popover.id = 'scale-row-popover'
	popover.className = 'scale-popover scale-popover--caret-right'
	popover.style.display = 'none'
	popover.innerHTML = `
		<div class="scale-popover-bridge"></div>
		<div class="scale-popover-caret"></div>
		<div class="scale-popover-content">
			<div id="scale-popover-header" class="scale-popover-header">
				<span id="scale-item-name">—</span> <span id="scale-row-progress">[—]</span>
			</div>
			<div class="scale-popover-readout">
				<span id="scale-readout-value" class="scale-readout-value">—</span>
				<span id="scale-readout-unit" class="scale-readout-unit"></span>
			</div>
			<div id="scale-readout-converted" class="scale-readout-converted">—</div>
			<div id="scale-status-text" class="scale-status-text">—</div>
		</div>
	`
	document.body.appendChild(popover)
	scaleState.overlay = popover
	bindScalePopoverPositionListeners()
}

function bindScalePopoverPositionListeners() {
	if (scaleState.positionListenersBound) return
	scaleState.positionListenersBound = true

	const reposition = () => {
		if (scaleState.connected && scaleState.overlay && scaleState.overlay.style.display !== 'none') {
			positionScalePopover()
		}
	}

	window.addEventListener('scroll', reposition, true)
	window.addEventListener('resize', reposition)

	if (typeof ResizeObserver !== 'undefined' && scaleState.overlay) {
		scaleState.popoverResizeObserver = new ResizeObserver(reposition)
		scaleState.popoverResizeObserver.observe(scaleState.overlay)
	}
}

function positionScalePopover() {
	if (!scaleState.overlay || !scaleState.frm || scaleState.activeRowIdx === null || !scaleState.config) {
		return
	}

	const itemsTableField = scaleState.config.items_table_field || 'items'
	const field = scaleState.frm.get_field(itemsTableField)
	if (!field || !field.grid) return

	const gridRows = field.grid.grid_rows || []
	const gridRow = gridRows[scaleState.activeRowIdx]
	if (!gridRow || !gridRow.wrapper || !gridRow.wrapper.length) return

	const rowRect = gridRow.wrapper[0].getBoundingClientRect()
	const popover = scaleState.overlay
	const popoverH = popover.offsetHeight
	const popoverW = popover.offsetWidth || 240
	const caretSize = 20
	const gap = 8
	const pad = 8
	const caretHeight = 40

	const rowCenterY = rowRect.top + rowRect.height / 2
	let top = rowCenterY - popoverH / 2
	top = Math.max(pad, Math.min(top, window.innerHeight - popoverH - pad))

	const gridRect = field.grid.wrapper[0].getBoundingClientRect()
	const spaceLeft = gridRect.left - pad
	const spaceRight = window.innerWidth - gridRect.right - pad
	const caret = popover.querySelector('.scale-popover-caret')
	const bridge = popover.querySelector('.scale-popover-bridge')

	let left
	let caretOnRight = true
	if (spaceLeft >= popoverW + gap + caretSize) {
		left = gridRect.left - popoverW - gap - caretSize
		popover.classList.remove('scale-popover--caret-left')
		popover.classList.add('scale-popover--caret-right')
		caretOnRight = true
	} else if (spaceRight >= popoverW + gap + caretSize) {
		left = gridRect.right + gap + caretSize
		popover.classList.remove('scale-popover--caret-right')
		popover.classList.add('scale-popover--caret-left')
		caretOnRight = false
	} else {
		left = pad
		popover.classList.remove('scale-popover--caret-left')
		popover.classList.add('scale-popover--caret-right')
		caretOnRight = true
	}

	popover.style.top = `${top}px`
	popover.style.left = `${left}px`
	popover.style.right = 'auto'

	if (caret) {
		let caretTop = rowCenterY - top - caretHeight / 2
		caretTop = Math.max(8, Math.min(caretTop, popoverH - caretHeight - 8))
		caret.style.top = `${caretTop}px`
	}

	if (bridge) {
		const bridgeHeight = Math.min(Math.max(rowRect.height - 4, 12), 32)
		const bridgeTop = rowCenterY - top - bridgeHeight / 2
		let bridgeLeft
		let bridgeWidth

		if (caretOnRight) {
			bridgeLeft = popoverW
			bridgeWidth = Math.max(0, gridRect.left - left - popoverW)
		} else {
			bridgeLeft = gridRect.right - left
			bridgeWidth = Math.max(0, left - gridRect.right)
		}

		bridge.style.top = `${bridgeTop}px`
		bridge.style.left = `${bridgeLeft}px`
		bridge.style.width = `${bridgeWidth}px`
		bridge.style.height = `${bridgeHeight}px`
		bridge.style.display = bridgeWidth > 2 ? 'block' : 'none'
	}

	ensureScaleReadoutInView(gridRow.wrapper[0], popover)
}

function ensureScaleReadoutInView(activeRowEl, popover) {
	const pad = 16
	const rowRect = activeRowEl.getBoundingClientRect()
	const popoverRect = popover.getBoundingClientRect()

	const minTop = Math.min(rowRect.top, popoverRect.top)
	const maxBottom = Math.max(rowRect.bottom, popoverRect.bottom)

	if (minTop < pad) {
		window.scrollBy({ top: minTop - pad, behavior: 'smooth' })
	} else if (maxBottom > window.innerHeight - pad) {
		window.scrollBy({ top: maxBottom - window.innerHeight + pad, behavior: 'smooth' })
	}
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

function shouldAutoadvanceOnZero() {
	const setting = scaleState.config && scaleState.config.autoadvance_on_zero
	return setting !== 0 && setting !== false
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
			if (isZero && isStable) {
				if (shouldAutoadvanceOnZero()) {
					advanceToNextRow()
				} else {
					scaleState.workflowState = 'ZERO_DETECTED'
					scaleState.lastStatusText = 'Ready for next'
				}
			} else if (isZero) {
				scaleState.lastStatusText = 'Stabilizing…'
			} else {
				scaleState.lastStatusText = 'Remove item'
			}
			break

		case 'ZERO_DETECTED':
			scaleState.lastStatusText = 'Ready for next'
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

	if (!items || items.length === 0) return

	const lastIdx = items.length - 1
	if (scaleState.activeRowIdx >= lastIdx) {
		scaleState.workflowState = 'WAITING'
		scaleState.stableReadingCount = 0
		scaleState.qtyFilled = false
		scaleState.lastStatusText = 'All items done — add a row for more'
		updatePopover()
		updateRowHighlight()
		return
	}

	scaleState.activeRowIdx += 1
	scaleState.workflowState = 'WAITING'
	scaleState.stableReadingCount = 0
	scaleState.qtyFilled = false
	scaleState.lastStatusText = 'Place item on scale'

	updatePopover()
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
		positionScalePopover()
	}
}

frappe.dom.set_style(`
	.scale-row-active {
		background: var(--yellow-highlight-color) !important;
		outline: 2px solid var(--yellow-100) !important;
	}

	.scale-popover {
		position: fixed;
		width: 240px;
		z-index: 2000;
		transition: top 200ms ease, left 200ms ease;
		font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
	}

	.scale-popover-content {
		background: var(--card-bg);
		border: 1px solid var(--border-color);
		border-radius: 6px;
		padding: 16px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.scale-popover--caret-right .scale-popover-content {
		border-right: 3px solid var(--yellow-100);
	}

	.scale-popover--caret-left .scale-popover-content {
		border-left: 3px solid var(--yellow-100);
	}

	.scale-popover-bridge {
		position: absolute;
		display: none;
		background: var(--yellow-highlight-color);
		border-top: 2px solid var(--yellow-100);
		border-bottom: 2px solid var(--yellow-100);
		pointer-events: none;
		z-index: 1;
	}

	.scale-popover-caret {
		position: absolute;
		width: 20px;
		height: 40px;
		transition: top 200ms ease;
		z-index: 2;
	}

	.scale-popover--caret-right .scale-popover-caret {
		right: -20px;
	}

	.scale-popover--caret-right .scale-popover-caret::before {
		content: '';
		position: absolute;
		inset: 0;
		background: var(--yellow-100);
		clip-path: polygon(0 0, 0 100%, 100% 50%);
	}

	.scale-popover--caret-right .scale-popover-caret::after {
		content: '';
		position: absolute;
		top: 2px;
		bottom: 2px;
		left: 0;
		width: 16px;
		background: var(--yellow-highlight-color);
		clip-path: polygon(0 0, 0 100%, 100% 50%);
	}

	.scale-popover--caret-left .scale-popover-caret {
		left: -20px;
	}

	.scale-popover--caret-left .scale-popover-caret::before {
		content: '';
		position: absolute;
		inset: 0;
		background: var(--yellow-100);
		clip-path: polygon(100% 0, 100% 100%, 0 50%);
	}

	.scale-popover--caret-left .scale-popover-caret::after {
		content: '';
		position: absolute;
		top: 2px;
		bottom: 2px;
		right: 0;
		width: 16px;
		background: var(--yellow-highlight-color);
		clip-path: polygon(100% 0, 100% 100%, 0 50%);
	}

	.scale-popover-header {
		font-size: 13px;
		color: var(--text-muted);
		margin-bottom: 12px;
		text-align: center;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.scale-popover-readout {
		text-align: center;
		margin-bottom: 8px;
		line-height: 1;
	}

	.scale-readout-value {
		font-size: 72px;
		font-weight: bold;
		color: var(--text-color);
		font-family: Monaco, Courier, monospace;
		white-space: nowrap;
	}

	.scale-readout-unit {
		font-size: 36px;
		font-weight: bold;
		color: var(--text-muted);
		font-family: Monaco, Courier, monospace;
		margin-left: 4px;
	}

	.scale-readout-converted {
		font-size: 36px;
		font-weight: 600;
		text-align: center;
		margin-bottom: 12px;
		color: var(--primary-color);
		font-family: Monaco, Courier, monospace;
		min-height: 1.2em;
	}

	.scale-status-text {
		font-size: 12px;
		color: var(--text-muted);
		text-align: center;
	}
`)
