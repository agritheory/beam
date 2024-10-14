// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import 'pinia'
import type { Router } from 'vue-router'

declare module 'pinia' {
	export interface PiniaCustomProperties {
		router: Router
	}
}

export {}
