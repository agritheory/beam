import { nextTick, onBeforeUnmount, watch, type Ref } from 'vue'

// Left between a shrunk list and the window's bottom.
const WINDOW_MARGIN = 8
// With less room than this below, a list keeps this many rows and runs past the window.
const MIN_ROWS = 4

type DropdownListState = {
	isOpen: () => boolean
	/** Options arrive after a list opens when its search is async, and each arrival is measured again. */
	optionCount: () => number
	activeIndex: () => number | null
}

/**
 * Keeps an open dropdown list in the window: its height is the smaller of `--sc-dropdown-max-height`
 * (the stylesheet's `max-height`) and the room left below it, never under about four rows, and the
 * option the arrow keys highlight is scrolled into sight.
 */
export function fitDropdownList(list: Readonly<Ref<HTMLElement | null>>, state: DropdownListState) {
	const fit = (event?: Event) => {
		const element = list.value
		// The list's own scrolling moves nothing it is measured against.
		if (!element || !state.isOpen() || event?.target === element) return
		element.style.maxHeight = ''
		const cap = Number.parseFloat(getComputedStyle(element).maxHeight)
		const row = element.querySelector('[role="option"]')?.getBoundingClientRect().height ?? 0
		const room = window.innerHeight - element.getBoundingClientRect().top - WINDOW_MARGIN
		const height = Math.max(room, MIN_ROWS * row)
		// `none` reads as NaN, and then the room below is the only limit.
		if (Number.isNaN(cap) || height < cap) element.style.maxHeight = `${Math.floor(height)}px`
	}

	const listen = () => {
		window.addEventListener('scroll', fit, { capture: true, passive: true })
		window.addEventListener('resize', fit, { passive: true })
	}
	const stopListening = () => {
		window.removeEventListener('scroll', fit, { capture: true })
		window.removeEventListener('resize', fit)
	}

	watch(
		() => state.isOpen(),
		open => {
			if (open) return listen()
			stopListening()
			if (list.value) list.value.style.maxHeight = ''
		}
	)

	// After the flush, not in it: a `v-show` list is still hidden while post-flush watchers run, and a
	// hidden list measures as sitting at the top of the window.
	watch(
		() => state.isOpen() && state.optionCount(),
		() => void nextTick(() => fit())
	)

	watch(
		() => state.activeIndex(),
		index => {
			if (index === null || index < 0) return
			// jsdom, where hosts test the forms they build, has no scrollIntoView.
			void nextTick(() =>
				list.value?.querySelectorAll('[role="option"]')[index]?.scrollIntoView?.({ block: 'nearest' })
			)
		},
		{ flush: 'post' }
	)

	onBeforeUnmount(stopListening)
}
