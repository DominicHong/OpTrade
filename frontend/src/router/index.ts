import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/pages/DashboardPage.vue'),
    },
    {
      path: '/trades',
      name: 'trades',
      component: () => import('@/pages/TradeListPage.vue'),
    },
    {
      path: '/trades/:id',
      name: 'trade-detail',
      component: () => import('@/pages/TradeDetailPage.vue'),
      props: true,
    },
    {
      path: '/portfolios',
      name: 'portfolios',
      component: () => import('@/pages/PortfolioManagementPage.vue'),
    },
    {
      path: '/portfolio',
      name: 'portfolio',
      component: () => import('@/pages/PortfolioAnalysisPage.vue'),
    },
    {
      path: '/scenario',
      name: 'scenario',
      component: () => import('@/pages/ScenarioPage.vue'),
    },
  ],
})

export default router
