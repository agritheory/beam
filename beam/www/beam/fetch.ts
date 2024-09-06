// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

const demandUrl = '/api/method/beam.beam.demand.demand.get_demand'

function getFetchUrl(url: string, params?: Record<string, any>) {
	let fragment: string
	if (params) {
		const query = new URLSearchParams(params)
		fragment = `${url}?${query.toString()}`
	} else {
		fragment = url
	}
	return fragment
}

export async function useFetch<T>(url: string, params?: Record<string, any>) {
	const fragment = getFetchUrl(url, params)
	const formattedUrl = new URL(fragment, window.location.origin)
	const response = await fetch(formattedUrl)
	const { data }: { data: T } = await response.json()
	return { data }
}

export async function useFetchDemand(params?: Record<string, any>) {
	// automatically fetch all pages of demand data based on parameters
	const url = getFetchUrl(demandUrl, params)
	return paginatedFetch(url)
}

// ref: https://observablehq.com/@xari/paginated_fetch
async function paginatedFetch(url: string, page: number = 1, previousResponse: any[] = []) {
	const pageFragment = `${url}&page=${page}`
	const formattedUrl = new URL(pageFragment, window.location.origin)
	const response = await fetch(formattedUrl)
	const data = await response.json()

	const combinedResponse = [...previousResponse, ...data.message]
	if (data.message.length !== 0) {
		page++
		return paginatedFetch(url, page, combinedResponse)
	}

	return { data: combinedResponse }
}
