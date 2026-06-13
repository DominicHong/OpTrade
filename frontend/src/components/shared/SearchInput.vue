<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  modelValue: string
  placeholder?: string
}>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const localValue = ref(props.modelValue)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

watch(() => props.modelValue, (v) => { localValue.value = v })

function onInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emit('update:modelValue', localValue.value)
  }, 300)
}
</script>

<template>
  <div class="search-input">
    <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
    </svg>
    <input
      v-model="localValue"
      type="text"
      :placeholder="placeholder || '搜索...'"
      @input="onInput"
    />
  </div>
</template>

<style scoped>
.search-input {
  display: flex;
  align-items: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 0 0.75rem;
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-fast);
}
.search-input:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-glow);
}
.search-input input {
  border: none;
  outline: none;
  padding: 0.5rem 0.5rem;
  font-size: 0.875rem;
  width: 240px;
  background: transparent;
  color: var(--color-text);
}
.search-input input::placeholder {
  color: var(--color-text-secondary);
  opacity: 0.7;
}
.search-icon {
  flex-shrink: 0;
  color: var(--color-text-secondary);
  opacity: 0.5;
}
.search-input:focus-within .search-icon {
  color: var(--color-primary);
  opacity: 1;
}
</style>
