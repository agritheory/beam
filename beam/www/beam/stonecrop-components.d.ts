// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

export {}

declare module 'vue' {
	export interface GlobalComponents {
		ActionFooter: (typeof import('@stonecrop/beam'))['ActionFooter']
		BeamArrow: (typeof import('@stonecrop/beam'))['BeamArrow']
		BeamBtn: (typeof import('@stonecrop/beam'))['BeamBtn']
		BeamDayDivider: (typeof import('@stonecrop/beam'))['BeamDayDivider']
		BeamFilter: (typeof import('@stonecrop/beam'))['BeamFilter']
		BeamFilterOption: (typeof import('@stonecrop/beam'))['BeamFilterOption']
		BeamHeading: (typeof import('@stonecrop/beam'))['BeamHeading']
		BeamMetadata: (typeof import('@stonecrop/beam'))['BeamMetadata']
		BeamModal: (typeof import('@stonecrop/beam'))['BeamModal']
		BeamModalOutlet: (typeof import('@stonecrop/beam'))['BeamModalOutlet']
		BeamProgress: (typeof import('@stonecrop/beam'))['BeamProgress']
		Confirm: (typeof import('@stonecrop/beam'))['Confirm']
		FixedTop: (typeof import('@stonecrop/beam'))['FixedTop']
		ItemCheck: (typeof import('@stonecrop/beam'))['ItemCheck']
		ItemCount: (typeof import('@stonecrop/beam'))['ItemCount']
		ListAnchor: (typeof import('@stonecrop/beam'))['ListAnchor']
		ListItem: (typeof import('@stonecrop/beam'))['ListItem']
		ListView: (typeof import('@stonecrop/beam'))['ListView']
		Navbar: (typeof import('@stonecrop/beam'))['Navbar']
		ScanInput: (typeof import('@stonecrop/beam'))['ScanInput']
		SegmentedDisplay: (typeof import('@stonecrop/beam'))['SegmentedDisplay']
		SplitColumn: (typeof import('@stonecrop/beam'))['SplitColumn']
		ToggleArrow: (typeof import('@stonecrop/beam'))['ToggleArrow']

		ACheckbox: (typeof import('@stonecrop/aform'))['ACheckbox']
		ACurrencyInput: (typeof import('@stonecrop/aform'))['ACurrencyInput']
		ADate: (typeof import('@stonecrop/aform'))['ADate']
		ADropdown: (typeof import('@stonecrop/aform'))['ADropdown']
		ASegmentedControl: (typeof import('@stonecrop/aform'))['ASegmentedControl']
		ABadge: (typeof import('@stonecrop/aform'))['ABadge']
		ADatePicker: (typeof import('@stonecrop/aform'))['ADatePicker']
		ADateTime: (typeof import('@stonecrop/aform'))['ADateTime']
		ADateTimeInput: (typeof import('@stonecrop/aform'))['ADateTimeInput']
		ADateSelection: (typeof import('@stonecrop/aform'))['ADateSelection']
		ADuration: (typeof import('@stonecrop/aform'))['ADuration']
		ADateRange: (typeof import('@stonecrop/aform'))['ADateRange']
		AFieldset: (typeof import('@stonecrop/aform'))['AFieldset']
		AFileAttach: (typeof import('@stonecrop/aform'))['AFileAttach']
		AForm: (typeof import('@stonecrop/aform'))['AForm']
		AFormLink: (typeof import('@stonecrop/aform'))['AFormLink']
		ANumericInput: (typeof import('@stonecrop/aform'))['ANumericInput']
		AQuantityInput: (typeof import('@stonecrop/aform'))['AQuantityInput']
		ATextInput: (typeof import('@stonecrop/aform'))['ATextInput']
		ATextboxInput: (typeof import('@stonecrop/aform'))['ATextboxInput']
	}
}
