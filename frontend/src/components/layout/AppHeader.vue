<script setup lang="ts">
import { useUiStore } from '@/stores/uiStore'

const ui = useUiStore()
</script>

<template>
  <header class="app-header">
    <button class="hamburger" aria-label="打开导航" @click="ui.toggleSidebar()">
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
    </button>
    <div class="header-brand">
      <span class="brand-icon">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M3 3v18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M7 16l4-6 4 4 5-8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
      <span class="header-title">OpTrade</span>
      <span class="header-subtitle">期权交易与风险管理系统</span>
    </div>
    <div class="header-spacer"></div>
    <div class="header-actions">
      <div class="header-badge">v0.1</div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  height: 56px;
  padding: 0 1.25rem;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.15);
  position: relative;
  z-index: 100;
}
.hamburger {
  background: none;
  border: none;
  cursor: pointer;
  margin-right: 1rem;
  color: var(--color-text-on-dark-secondary);
  padding: 6px;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
}
.hamburger:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--color-text-on-dark);
}
.header-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.brand-icon {
  display: flex;
  align-items: center;
  color: var(--color-primary-light);
}
.header-title {
  font-weight: 700;
  font-size: 1.1rem;
  color: #ffffff;
  letter-spacing: -0.02em;
}
.header-subtitle {
  font-size: 0.75rem;
  color: var(--color-text-on-dark-secondary);
  margin-left: 0.5rem;
  padding-left: 0.5rem;
  border-left: 1px solid rgba(148, 163, 184, 0.3);
}
.header-spacer { flex: 1; }
.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.header-badge {
  font-size: 0.65rem;
  font-weight: 600;
  color: var(--color-primary-lighter);
  background: rgba(59, 130, 246, 0.15);
  padding: 2px 8px;
  border-radius: 20px;
  letter-spacing: 0.03em;
}
</style>
