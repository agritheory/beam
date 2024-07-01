// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

if (!self.define) {
	let e,
		i = {}
	const n = (n, r) => (
		(n = new URL(n + '.js', r).href),
		i[n] ||
			new Promise(i => {
				if ('document' in self) {
					const e = document.createElement('script')
					;(e.src = n), (e.onload = i), document.head.appendChild(e)
				} else (e = n), importScripts(n), i()
			}).then(() => {
				let e = i[n]
				if (!e) throw new Error(`Module ${n} didn’t register its module`)
				return e
			})
	)
	self.define = (r, s) => {
		const c = e || ('document' in self ? document.currentScript.src : '') || location.href
		if (i[c]) return
		let d = {}
		const t = e => n(e, c),
			o = { module: { uri: c }, exports: d, require: t }
		i[c] = Promise.all(r.map(e => o[e] || t(e))).then(e => (s(...e), d))
	}
}
define(['./workbox-5ffe50d4'], function (e) {
	'use strict'
	self.skipWaiting(),
		e.clientsClaim(),
		e.precacheAndRoute(
			[
				{ url: 'index.css', revision: 'b0efc6eb5892dd4bf0c5e329f158ecc9' },
				{ url: 'index.html', revision: 'dbc32782c2548aea05c5b1158c6425a4' },
				{ url: 'index.js', revision: '99fbe4fd35c256edc77cac680d1a5b71' },
				{ url: 'manifest.webmanifest', revision: 'e9af967f7d8cecade95614b0a1bd9de1' },
				{ url: 'registerSW.js', revision: '1872c500de691dce40960bb85481de07' },
				{ url: 'manifest.webmanifest', revision: 'e9af967f7d8cecade95614b0a1bd9de1' },
			],
			{}
		),
		e.cleanupOutdatedCaches(),
		e.registerRoute(new e.NavigationRoute(e.createHandlerBoundToURL('index.html')))
})
//# sourceMappingURL=sw.js.map
