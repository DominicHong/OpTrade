<script setup lang="ts">
defineProps<{ message?: string }>()
</script>

<template>
  <div class="loading-spinner">
    <div class="spinner-ring">
      <div class="spinner-ring-inner"></div>
    </div>
    <p v-if="message" class="spinner-message">{{ message }}</p>
  </div>
</template>

<style scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
}
.spinner-ring {
  width: 40px;
  height: 40px;
  position: relative;
}
.spinner-ring-inner {
  width: 100%;
  height: 100%;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.spinner-message {
  margin-top: 1rem;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}
</style>
