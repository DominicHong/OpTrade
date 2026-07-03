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
      path: '/option-trades',
      name: 'option-trades',
      component: () => import('@/pages/OptionTradeListPage.vue'),
    },
    {
      path: '/option-trades/:id',
      name: 'option-trade-detail',
      component: () => import('@/pages/OptionTradeDetailPage.vue'),
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
    {
      path: '/curves',
      name: 'curves',
      component: () => import('@/pages/CurveManagementPage.vue'),
    },
    {
      path: '/exchange-rates',
      name: 'exchange-rates',
      component: () => import('@/pages/ExchangeRateManagementPage.vue'),
    },
  ],
})

export default router
