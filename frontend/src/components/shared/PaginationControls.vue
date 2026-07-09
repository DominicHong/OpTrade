<script setup lang="ts">
const props = defineProps<{
  page: number
  totalPages: number
}>()

const emit = defineEmits<{
  (e: 'update:page', value: number): void
}>()

function go(p: number) {
  if (p >= 1 && p <= props.totalPages) emit('update:page', p)
}
</script>

<template>
  <div v-if="totalPages > 1" class="pagination">
    <button class="page-btn" :disabled="page <= 1" @click="go(1)">«</button>
    <button class="page-btn" :disabled="page <= 1" @click="go(page - 1)">‹</button>
    <span class="page-info">{{ page }} / {{ totalPages }}</span>
    <button class="page-btn" :disabled="page >= totalPages" @click="go(page + 1)">›</button>
    <button class="page-btn" :disabled="page >= totalPages" @click="go(totalPages)">»</button>
  </div>
</template>
