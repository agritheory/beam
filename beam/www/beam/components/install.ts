// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import type { App } from 'vue'

import ADropdown from './ADropdown.vue'
import ANumericInput from './ANumericInput.vue'
import BeamBtn from './BeamBtn.vue'
import BeamDayDivider from './BeamDayDivider.vue'
import BeamFilter from './BeamFilter.vue'
import BeamFilterOption from './BeamFilterOption.vue'
import BeamHeading from './BeamHeading.vue'
import BeamMetadata from './BeamMetadata.vue'
import BeamModal from './BeamModal.vue'
import BeamModalOutlet from './BeamModalOutlet.vue'
import Confirm from './Confirm.vue'
import ItemCheck from './ItemCheck.vue'
import ItemCount from './ItemCount.vue'
import ListAnchor from './ListAnchor.vue'
import ListItem from './ListItem.vue'
import ListView from './ListView.vue'
import Navbar from './Navbar.vue'
import ScanInput from './ScanInput.vue'
import SplitColumn from './SplitColumn.vue'
import ToggleArrow from './ToggleArrow.vue'

export function installStonecropComponents(app: App) {
	app.component('ADropdown', ADropdown)
	app.component('ANumericInput', ANumericInput)
	app.component('BeamBtn', BeamBtn)
	app.component('BeamDayDivider', BeamDayDivider)
	app.component('BeamFilter', BeamFilter)
	app.component('BeamFilterOption', BeamFilterOption)
	app.component('BeamHeading', BeamHeading)
	app.component('BeamMetadata', BeamMetadata)
	app.component('BeamModal', BeamModal)
	app.component('BeamModalOutlet', BeamModalOutlet)
	app.component('Confirm', Confirm)
	app.component('ItemCheck', ItemCheck)
	app.component('ItemCount', ItemCount)
	app.component('ListAnchor', ListAnchor)
	app.component('ListItem', ListItem)
	app.component('ListView', ListView)
	app.component('Navbar', Navbar)
	app.component('ScanInput', ScanInput)
	app.component('SplitColumn', SplitColumn)
	app.component('ToggleArrow', ToggleArrow)
}
