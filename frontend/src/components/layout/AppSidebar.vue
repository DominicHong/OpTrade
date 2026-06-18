<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useUiStore } from '@/stores/uiStore'

const router = useRouter()
const route = useRoute()
const ui = useUiStore()

const navItems = [
  { path: '/', label: '仪表盘', icon: 'dashboard' },
  { path: '/trades', label: '交易管理', icon: 'trades' },
  { path: '/portfolios', label: '投组管理', icon: 'portfolios' },
  { path: '/portfolio', label: '组合分析', icon: 'portfolio' },
  { path: '/scenario', label: '情景分析', icon: 'scenario' },
]

const iconPaths: Record<string, string> = {
  dashboard: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  trades: 'M4 6h16M4 10h16M4 14h10M4 18h7',
  import: 'M12 3v12m0 0l-4-4m4 4l4-4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2',
  portfolio: 'M3 3v18h18M7 16l4-6 4 4 5-8',
  portfolios: 'M20 7h-4l-2-3H8L6 4H2v16h20V7zM4 18V7h2l2-3h6l2 3h4v11H4z',
  scenario: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z',
}

function navigate(path: string) {
  router.push(path)
}
</script>

<template>
  <aside class="app-sidebar" :class="{ collapsed: ui.sidebarCollapsed }">
    <nav class="sidebar-nav">
      <div
        v-for="item in navItems"
        :key="item.path"
        class="nav-item"
        :class="{ active: route.path === item.path || (item.path !== '/' && route.path.startsWith(item.path)) }"
        @click="navigate(item.path)"
      >
        <span class="nav-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path :d="iconPaths[item.icon]" />
          </svg>
        </span>
        <span class="nav-label">{{ item.label }}</span>
      </div>
    </nav>
  </aside>
</template>

<style scoped>
.app-sidebar {
  width: 220px;
  background: linear-gradient(180deg, #0f172a 0%, #162032 100%);
  border-right: 1px solid rgba(59, 130, 246, 0.1);
  transition: width var(--transition);
  overflow: hidden;
  flex-shrink: 0;
}
.app-sidebar.collapsed {
  width: 0;
  border-right: none;
}
.sidebar-nav {
  padding: 0.75rem 0.5rem;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 0.85rem;
  cursor: pointer;
  font-size: 0.85rem;
  color: var(--color-text-on-dark-secondary);
  border-radius: var(--radius);
  transition: all var(--transition-fast);
  margin-bottom: 2px;
  position: relative;
}
.nav-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--color-text-on-dark);
}
.nav-item.active {
  background: rgba(59, 130, 246, 0.15);
  color: var(--color-primary-light);
  font-weight: 600;
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background: var(--color-primary);
  border-radius: 0 3px 3px 0;
}
.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 20px;
  height: 20px;
}
.nav-label {
  white-space: nowrap;
  overflow: hidden;
}
</style>
