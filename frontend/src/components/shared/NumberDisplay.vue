<script setup lang="ts">
import { computed } from 'vue'
import { formatNumber } from '@/utils/format'

const props = withDefaults(defineProps<{
  value: number | null | undefined
  decimals?: number
  showSign?: boolean
  colorCode?: boolean
}>(), {
  decimals: 2,
  showSign: false,
  colorCode: false,
})

const displayValue = computed(() => formatNumber(props.value, props.decimals))
const cssClass = computed(() => {
  if (!props.colorCode || props.value === null || props.value === undefined) return ''
  if (props.value > 0) return 'num-positive'
  if (props.value < 0) return 'num-negative'
  return ''
})
</script>

<template>
  <span :class="cssClass" :title="String(value ?? '--')">
    <template v-if="showSign && value !== null && value !== undefined && value > 0">+</template>
    {{ displayValue }}
  </span>
</template>

<style scoped>
.num-positive { color: var(--color-positive); }
.num-negative { color: var(--color-negative); }
</style>
