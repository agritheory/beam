// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

if ('serviceWorker' in navigator) {
	window.addEventListener('load', () => {
		navigator.serviceWorker.register('/sw.js', { scope: '/' })
	})
}
