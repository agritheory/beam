// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'

import { useFetch } from './fetch.js'
import { ParentDoctype } from './types/index.js'

export const useDataStore = defineStore('form', {
	state: () => ({
		doc: {} as ParentDoctype,
	}),

	actions: {
		async fetchDoc(doctype: string, name: string) {
			const { data } = await useFetch<ParentDoctype>(`/api/resource/${doctype}/${name}`)
			this.doc = data
		},
	},
})
