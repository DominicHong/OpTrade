<script setup lang="ts">
defineProps<{
  show: boolean
  count: number
  label: string
}>()

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()
</script>

<template>
  <div v-if="show" class="modal-overlay" @mousedown="$emit('cancel')" @click="$emit('cancel')">
    <div class="modal modal-sm" @mousedown.stop @click.stop>
      <div class="modal-header">
        <h3>确认删除</h3>
        <button class="modal-close" @click="$emit('cancel')">&times;</button>
      </div>
      <div class="modal-body">
        <p>确定要删除选中的 {{ count }} 条{{ label }}吗？此操作不可撤销。</p>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" @click="$emit('cancel')">取消</button>
        <button class="btn-danger" @click="$emit('confirm')">确认删除</button>
      </div>
    </div>
  </div>
</template>
