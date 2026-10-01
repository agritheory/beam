// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

export {}

declare module 'vue' {
	export interface GlobalComponents {
		BeamBtn: new () => { $props: import('vue').ButtonHTMLAttributes }
		BeamFilter: (typeof import('@stonecrop/beam'))['BeamFilter']
		BeamFilterOption: (typeof import('@stonecrop/beam'))['BeamFilterOption']
		BeamHeading: (typeof import('@stonecrop/beam'))['BeamHeading']
		BeamMetadata: (typeof import('@stonecrop/beam'))['BeamMetadata']
		BeamModal: (typeof import('@stonecrop/beam'))['BeamModal']
		BeamModalOutlet: (typeof import('@stonecrop/beam'))['BeamModalOutlet']
		Confirm: (typeof import('@stonecrop/beam'))['Confirm']
		ListView: (typeof import('@stonecrop/beam'))['ListView']
		Navbar: (typeof import('@stonecrop/beam'))['Navbar']
		ScanInput: (typeof import('@stonecrop/beam'))['ScanInput']
		SplitColumn: (typeof import('@stonecrop/beam'))['SplitColumn']

		ADropdown: (typeof import('@stonecrop/aform'))['ADropdown']
		ANumericInput: (typeof import('@stonecrop/aform'))['ANumericInput']
	}
}
