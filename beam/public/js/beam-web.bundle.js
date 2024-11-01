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

// remove redirect-to query parameter on login page for mobile users
document.addEventListener('DOMContentLoaded', function () {
	if (window.location.pathname === '/login') {
		function isMobileDevice() {
			return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
		}
		if (isMobileDevice()) {
			const url = new URL(window.location.href)
			if (url.searchParams.has('redirect-to')) {
				url.searchParams.delete('redirect-to')
				window.history.replaceState({}, document.title, url.toString())
			}
		}
	}
})
