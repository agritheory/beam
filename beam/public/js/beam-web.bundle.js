// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

// specifically remove Frappe website theming for the Beam page
if (window.location.pathname === '/beam') {
	const stylesheets = document.querySelectorAll('link[rel=stylesheet]')
	for (const stylesheet of stylesheets) {
		if (stylesheet.href.includes('assets/frappe/dist/css/website.bundle')) {
			stylesheet.parentNode.removeChild(stylesheet)
		}
	}
}
