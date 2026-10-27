// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

export {}

declare module 'vue' {
	export interface GlobalComponents {
		ADropdown: (typeof import('@/components/ADropdown.vue'))['default']
		ANumericInput: (typeof import('@/components/ANumericInput.vue'))['default']
		BeamBtn: import('vue').DefineComponent<import('vue').ButtonHTMLAttributes>
		BeamDayDivider: (typeof import('@/components/BeamDayDivider.vue'))['default']
		BeamFilter: (typeof import('@/components/BeamFilter.vue'))['default']
		BeamFilterOption: (typeof import('@/components/BeamFilterOption.vue'))['default']
		BeamHeading: (typeof import('@/components/BeamHeading.vue'))['default']
		BeamMetadata: (typeof import('@/components/BeamMetadata.vue'))['default']
		BeamModal: (typeof import('@/components/BeamModal.vue'))['default']
		BeamModalOutlet: (typeof import('@/components/BeamModalOutlet.vue'))['default']
		Confirm: (typeof import('@/components/Confirm.vue'))['default']
		ItemCheck: (typeof import('@/components/ItemCheck.vue'))['default']
		ItemCount: (typeof import('@/components/ItemCount.vue'))['default']
		ListAnchor: (typeof import('@/components/ListAnchor.vue'))['default']
		ListItem: (typeof import('@/components/ListItem.vue'))['default']
		ListView: (typeof import('@/components/ListView.vue'))['default']
		Navbar: (typeof import('@/components/Navbar.vue'))['default']
		ScanInput: (typeof import('@/components/ScanInput.vue'))['default']
		SplitColumn: (typeof import('@/components/SplitColumn.vue'))['default']
		ToggleArrow: (typeof import('@/components/ToggleArrow.vue'))['default']
	}
}
