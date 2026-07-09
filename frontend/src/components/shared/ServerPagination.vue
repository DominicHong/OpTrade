<script setup lang="ts">
defineProps<{
  page: number
  totalPages: number
  total: number
}>()

const emit = defineEmits<{
  (e: 'update:page', value: number): void
}>()
</script>

<template>
  <div class="pagination" v-if="total > 0">
    <button class="page-btn" :disabled="page <= 1" @click="emit('update:page', page - 1)">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
      上一页
    </button>
    <span class="page-info">第 <strong>{{ page }}</strong> / {{ totalPages }} 页 <span class="page-total">(共 {{ total }} 条)</span></span>
    <button class="page-btn" :disabled="page >= totalPages" @click="emit('update:page', page + 1)">
      下一页
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>
    </button>
  </div>
</template>
