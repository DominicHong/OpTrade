<script setup lang="ts">
import { useUiStore } from '@/stores/uiStore'

const ui = useUiStore()

function iconFor(type: string): string {
  switch (type) {
    case 'success': return '✓'
    case 'error': return '✕'
    case 'warning': return '!'  
    case 'info':
    default: return 'ℹ'
  }
}
</script>

<template>
  <TransitionGroup
    tag="div"
    name="toast"
    class="toast-container"
  >
    <div
      v-for="n in ui.notifications"
      :key="n.id"
      class="toast"
      :class="`toast--${n.type}`"
      role="alert"
    >
      <span class="toast__icon">{{ iconFor(n.type) }}</span>
      <span class="toast__message">{{ n.message }}</span>
      <button
        class="toast__close"
        aria-label="关闭"
        @click="ui.removeNotification(n.id)"
      >
        ✕
      </button>
    </div>
  </TransitionGroup>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 280px;
  max-width: 420px;
  padding: 0.85rem 1rem;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
  pointer-events: auto;
  font-size: 0.875rem;
  color: var(--color-text);
}

.toast--success {
  border-left: 4px solid var(--color-positive);
}
.toast--error {
  border-left: 4px solid var(--color-negative);
}
.toast--warning {
  border-left: 4px solid var(--color-warning);
}
.toast--info {
  border-left: 4px solid var(--color-primary);
}

.toast__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  flex-shrink: 0;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 700;
  color: #fff;
}
.toast--success .toast__icon { background: var(--color-positive); }
.toast--error .toast__icon { background: var(--color-negative); }
.toast--warning .toast__icon { background: var(--color-warning); }
.toast--info .toast__icon { background: var(--color-primary); }

.toast__message {
  flex: 1;
  line-height: 1.4;
}

.toast__close {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: 0.8rem;
  padding: 0.2rem;
  line-height: 1;
  transition: color var(--transition-fast);
}
.toast__close:hover {
  color: var(--color-text);
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
