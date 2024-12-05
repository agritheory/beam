<template>
    <div ref="autocomplete" class="autocomplete" :class="{ isOpen: isOpen }">
        <div class="input-wrapper">
            <input
                ref="adropdown"
                type="text"
                @input="onChange"
                @focus="onChange"
                v-model="search"
                @keydown.down="onArrowDown"
                @keydown.up="onArrowUp"
                @keydown.enter="onEnter" />

            <ul id="autocomplete-results" v-show="isOpen" class="autocomplete-results">
                <li class="loading autocomplete-result" v-if="isLoading">Loading results...</li>
                <li
                    v-else
                    v-for="(result, i) in results"
                    :key="i"
                    @click.stop="setResult(result)"
                    class="autocomplete-result"
                    :class="{ 'is-active': i === arrowCounter }">
                    {{ result }}
                </li>
            </ul>
            <label>{{ label }}</label>
        </div>
    </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';

const { label, items, isAsync } = defineProps<{
    label: string;
    items?: string[];
    isAsync?: boolean;
}>();

const emit = defineEmits(['filterChanged']);

const autocomplete = ref<HTMLElement | null>(null); // Ref para el contenedor
const results = ref(items);
const search = defineModel<string>();
const isLoading = ref(false);
const arrowCounter = ref(0);
const isOpen = ref(false);

onMounted(() => {
    document.addEventListener('click', handleClickOutside);
    filterResults();
});

onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside);
});

const handleClickOutside = (event: MouseEvent) => {
    if (autocomplete.value && !autocomplete.value.contains(event.target as Node)) {
        closeResults();
        arrowCounter.value = 0;
    }
};

const onChange = () => {
    isOpen.value = true;
    if (isAsync) {
        isLoading.value = true;
        emit('filterChanged', search.value);
    } else {
        filterResults();
    }
};

const setResult = (result: string) => {
    search.value = result;
    closeResults(result);
};

const closeResults = (result?: string) => {
    isOpen.value = false;
    if (!items.includes(result || search.value)) {
        search.value = '';
    }
};

const filterResults = () => {
    if (!search.value) {
        results.value = items;
    } else {
        results.value = items.filter(item =>
            item.toLowerCase().includes(search.value.toLowerCase())
        );
    }
};

const onArrowDown = () => {
    if (arrowCounter.value < results.value.length) {
        arrowCounter.value += 1;
    }
};

const onArrowUp = () => {
    if (arrowCounter.value > 0) {
        arrowCounter.value -= 1;
    }
};

const onEnter = () => {
    search.value = results.value[arrowCounter.value];
    closeResults(results.value[arrowCounter.value]);
    arrowCounter.value = 0;
};

// const openWithSearch = () => {
// 	search.value = ''
// 	onChange()
// 	mopInput.value.focus()
// }
</script>

<style scoped>
/* variables taken from here: https://github.com/frappe/frappe/blob/version-13/frappe/public/scss/common/awesomeplete.scss */
.autocomplete {
	position: relative;
}

.input-wrapper {
	min-width: 40ch;
	border: 1px solid transparent;
	padding: 0rem;
	margin: 0rem;
	margin-right: 1ch;
}

input {
	width: calc(100% - 1ch);
	outline: 1px solid transparent;
	border: 1px solid #cccccc;
	padding: 1ch 0.5ch 0.5ch 1ch;
	margin: calc(1.15rem / 2) 0 0 0;
	min-height: 1.15rem;
	border-radius: 0.25rem;
}

input:focus {
	border: 1px solid #000000;
	border-radius: 0.25rem 0.25rem 0 0;
	border-bottom: none;
}

label {
	display: block;
	min-height: 1.15rem;
	padding: 0rem;
	margin: 0rem;
	border: 1px solid transparent;
	margin-bottom: 0.25rem;
	z-index: 2;
	font-size: 80%;
	position: absolute;
	background: white;
	margin: calc(-1.5rem - calc(2.15rem / 2)) 0 0 1ch;
	padding: 0 0.25ch 0 0.25ch;
}

.autocomplete-results {
	position: absolute;
	width: calc(100% - 1ch + 1.5px);
	z-index: 999;
	padding: 0;
	margin: 0;
	color: #000000;
	border: 1px solid #000000;
	border-radius: 0 0 0.25rem 0.25rem;
	border-top: none;
    background-color: #fff;
}

.autocomplete-result {
	list-style: none;
	text-align: left;
	padding: 4px 6px;
	cursor: pointer;
}

.autocomplete-result.is-active,
.autocomplete-result:hover {
	background-color: #eeeeee;
	color: #000000;
}
</style>