import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const sidebarCollapsed = ref(false)
  const globalLoading = ref(false)
  const notifications = ref<Array<{ id: number; type: string; message: string }>>([])
  let nextId = 0

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setLoading(val: boolean) {
    globalLoading.value = val
  }

  function addNotification(type: 'success' | 'error' | 'warning' | 'info', message: string) {
    const id = nextId++
    notifications.value.push({ id, type, message })
    // Auto-dismiss after 5 seconds
    setTimeout(() => removeNotification(id), 5000)
  }

  function removeNotification(id: number) {
    notifications.value = notifications.value.filter(n => n.id !== id)
  }

  return {
    sidebarCollapsed, globalLoading, notifications,
    toggleSidebar, setLoading, addNotification, removeNotification,
  }
})
