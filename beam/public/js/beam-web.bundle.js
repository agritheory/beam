// specifically remove Frappe website theming for the Beam page
if (window.location.pathname === '/beam') {
	const stylesheets = document.querySelectorAll('link[rel=stylesheet]')
	for (const stylesheet of stylesheets) {
		if (stylesheet.href.includes('assets/frappe/dist/css/website.bundle')) {
			stylesheet.parentNode.removeChild(stylesheet)
		}
	}
}
