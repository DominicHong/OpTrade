<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { usePortfolioStore } from '@/stores/portfolioStore'
import type { Portfolio } from '@/types/portfolio'

const props = defineProps<{
  modelValue: string | null | undefined
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
  'update:portfolioId': [value: number | null]
}>()

const store = usePortfolioStore()

const inputText = ref(props.modelValue || '')
const isOpen = ref(false)
const highlightedIndex = ref(-1)

// Sync external modelValue changes back to inputText
watch(() => props.modelValue, (val) => {
  if (val !== undefined && val !== null) {
    inputText.value = val
  }
})

// Load portfolios on mount
onMounted(() => {
  if (store.portfolios.length === 0) {
    store.loadPortfolios()
  }
})

// Filter portfolios by typed text
const filteredPortfolios = computed(() => {
  const query = inputText.value.toLowerCase().trim()
  if (!query) return store.portfolios
  return store.portfolios.filter(p =>
    p.name.toLowerCase().includes(query)
  )
})

function onInput() {
  // As user types, emit the text value (but no portfolio_id until selection)
  emit('update:modelValue', inputText.value || null)
  emit('update:portfolioId', null)
  isOpen.value = true
  highlightedIndex.value = -1
}

function onFocus() {
  isOpen.value = true
}

function selectPortfolio(p: Portfolio) {
  inputText.value = p.name
  emit('update:modelValue', p.name)
  emit('update:portfolioId', p.id)
  isOpen.value = false
  highlightedIndex.value = -1
}

function onKeydown(e: KeyboardEvent) {
  if (!isOpen.value || filteredPortfolios.value.length === 0) {
    if (e.key === 'Enter') {
      e.preventDefault()
    }
    return
  }

  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault()
      highlightedIndex.value = Math.min(highlightedIndex.value + 1, filteredPortfolios.value.length - 1)
      break
    case 'ArrowUp':
      e.preventDefault()
      highlightedIndex.value = Math.max(highlightedIndex.value - 1, -1)
      break
    case 'Enter':
      e.preventDefault()
      if (highlightedIndex.value >= 0 && highlightedIndex.value < filteredPortfolios.value.length) {
        selectPortfolio(filteredPortfolios.value[highlightedIndex.value])
      }
      break
    case 'Escape':
      isOpen.value = false
      highlightedIndex.value = -1
      break
  }
}

function onBlur() {
  // Delay to allow click on dropdown item
  setTimeout(() => {
    isOpen.value = false
    highlightedIndex.value = -1
  }, 200)
}
</script>

<template>
  <div class="autocomplete-wrapper">
    <input
      type="text"
      v-model="inputText"
      :placeholder="placeholder || '搜索并选择投组...'"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
      @keydown="onKeydown"
      autocomplete="off"
    />
    <ul v-if="isOpen && filteredPortfolios.length > 0" class="autocomplete-dropdown">
      <li
        v-for="(p, idx) in filteredPortfolios"
        :key="p.id"
        class="autocomplete-item"
        :class="{ highlighted: idx === highlightedIndex }"
        @mousedown.prevent="selectPortfolio(p)"
      >
        <span class="ac-name">{{ p.name }}</span>
        <span class="ac-count">{{ p.trade_count }} 笔交易</span>
      </li>
    </ul>
    <div v-if="isOpen && inputText.trim() && filteredPortfolios.length === 0" class="autocomplete-dropdown">
      <div class="autocomplete-empty">
        未找到匹配的投组。请先在
        <router-link to="/portfolios" @click.stop="isOpen = false">投组管理</router-link>
        中创建。
      </div>
    </div>
  </div>
</template>

<style scoped>
.autocomplete-wrapper {
  position: relative;
  width: 100%;
}

.autocomplete-wrapper input {
  width: 100%;
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.8125rem;
  background: var(--color-bg);
  color: var(--color-text);
  transition: border-color var(--transition-fast);
  box-sizing: border-box;
}
.autocomplete-wrapper input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-bg);
}

.autocomplete-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 200px;
  overflow-y: auto;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-top: none;
  border-radius: 0 0 var(--radius) var(--radius);
  box-shadow: var(--shadow-md);
  z-index: 100;
  list-style: none;
  margin: 0;
  padding: 0.25rem 0;
}

.autocomplete-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.45rem 0.75rem;
  cursor: pointer;
  font-size: 0.8125rem;
  transition: background var(--transition-fast);
}
.autocomplete-item:hover,
.autocomplete-item.highlighted {
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

.ac-name {
  font-weight: 500;
}
.ac-count {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
}

.autocomplete-empty {
  padding: 0.6rem 0.75rem;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  text-align: center;
}
.autocomplete-empty a {
  color: var(--color-primary);
  text-decoration: underline;
}
.autocomplete-empty a:hover {
  color: var(--color-primary-light);
}
</style>
