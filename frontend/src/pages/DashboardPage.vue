<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchDashboardSummary } from '@/api/dashboard'
import { useOptionTradeStore } from '@/stores/optionTradeStore'
import { toWan } from '@/utils/format'
import type { DashboardSummary } from '@/types/api'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import NumberDisplay from '@/components/shared/NumberDisplay.vue'

const summary = ref<DashboardSummary | null>(null)
const loading = ref(true)
const tradeStore = useOptionTradeStore()

onMounted(async () => {
  try {
    summary.value = await fetchDashboardSummary()
    await tradeStore.loadTrades({ page_size: 10, sort_by: 'expiry_date', sort_order: 'asc' })
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h1>仪表盘</h1>
      <p class="page-desc">期权交易与风险概览</p>
    </div>

    <div v-if="loading"><LoadingSpinner message="加载仪表盘数据..." /></div>

    <template v-else-if="summary">
      <!-- Stats Cards -->
      <div class="stats-row">
        <div class="stat-card stat-card--primary">
          <div class="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ summary.total_trades }}</span>
            <span class="stat-label">总交易笔数</span>
          </div>
        </div>
        <div class="stat-card stat-card--blue">
          <div class="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ summary.total_portfolios }}</span>
            <span class="stat-label">投资组合数</span>
          </div>
        </div>
        <div class="stat-card stat-card--teal">
          <div class="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ summary.total_counterparties }}</span>
            <span class="stat-label">交易对手</span>
          </div>
        </div>
        <div class="stat-card stat-card--indigo">
          <div class="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          </div>
          <div class="stat-content">
            <span class="stat-value"><NumberDisplay :value="toWan(summary.total_notional1)" /></span>
            <span class="stat-label">总名义本金(万)</span>
          </div>
        </div>
      </div>

      <!-- Sections -->
      <div class="dashboard-grid">
        <!-- Notional by CCY -->
        <section class="card">
          <div class="card-header">
            <h3>货币对名义本金分布(万)</h3>
          </div>
          <table class="simple-table" v-if="Object.keys(summary.notional_by_ccy).length">
            <tr v-for="(val, ccy) in summary.notional_by_ccy" :key="ccy">
              <td class="ccy-label">{{ ccy }}</td>
              <td class="num"><NumberDisplay :value="toWan(val)" /></td>
            </tr>
          </table>
          <p v-else class="empty-text">暂无数据</p>
        </section>

        <!-- Trades by Type -->
        <section class="card">
          <div class="card-header">
            <h3>按交易类型分布</h3>
          </div>
          <table class="simple-table" v-if="Object.keys(summary.trades_by_type).length">
            <tr v-for="(count, type) in summary.trades_by_type" :key="type">
              <td>
                <span :class="type === 'CALL' ? 'type-badge type-badge--call' : 'type-badge type-badge--put'">{{ type }}</span>
              </td>
              <td class="num">{{ count }}</td>
            </tr>
          </table>
          <p v-else class="empty-text">暂无数据</p>
        </section>

        <!-- Recent Trades -->
        <section class="card">
          <div class="card-header">
            <h3>最近交易</h3>
            <span class="card-subtitle">按到期日排序</span>
          </div>
          <table class="simple-table" v-if="tradeStore.trades.length">
            <tr v-for="t in tradeStore.trades.slice(0, 10)" :key="t.id">
              <td class="trade-id">{{ t.trade_id }}</td>
              <td>{{ t.ccy_pair }}</td>
              <td>
                <span :class="t.trade_type === 'CALL' ? 'type-badge type-badge--call' : 'type-badge type-badge--put'">
                  {{ t.trade_type }}
                </span>
                <span class="direction-badge">{{ t.direction }}</span>
              </td>
              <td class="num">{{ t.expiry_date }}</td>
            </tr>
          </table>
          <p v-else class="empty-text">暂无交易数据</p>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page-header { margin-bottom: 1.5rem; }
.page-desc { color: var(--color-text-secondary); font-size: 0.875rem; margin-top: 0.25rem; }

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1.75rem;
}
.stat-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: var(--shadow-sm);
  transition: all var(--transition);
  position: relative;
  overflow: hidden;
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}
.stat-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.stat-card--primary::before { background: linear-gradient(90deg, var(--color-primary), var(--color-primary-light)); }
.stat-card--blue::before { background: linear-gradient(90deg, #2563eb, #60a5fa); }
.stat-card--teal::before { background: linear-gradient(90deg, #0d9488, #5eead4); }
.stat-card--indigo::before { background: linear-gradient(90deg, #6366f1, #a5b4fc); }

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-card--primary .stat-icon { background: var(--color-primary-bg); color: var(--color-primary); }
.stat-card--blue .stat-icon { background: #eff6ff; color: #2563eb; }
.stat-card--teal .stat-icon { background: #f0fdfa; color: #0d9488; }
.stat-card--indigo .stat-icon { background: #eef2ff; color: #6366f1; }

.stat-content { display: flex; flex-direction: column; }
.stat-value { display: block; font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; }
.stat-label { display: block; font-size: 0.75rem; color: var(--color-text-secondary); margin-top: 0.15rem; }

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
}
.card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition);
}
.card:hover { box-shadow: var(--shadow-md); }
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.85rem;
}
.card h3 { font-size: 0.9375rem; }
.card-subtitle { font-size: 0.7rem; color: var(--color-text-secondary); }
.simple-table { width: 100%; font-size: 0.8125rem; }
.simple-table td { padding: 0.4rem 0; border-bottom: 1px solid var(--color-border-light); }
.simple-table .num { text-align: right; font-weight: 500; font-variant-numeric: tabular-nums; }
.ccy-label { font-weight: 600; color: var(--color-primary-dark); }
.trade-id { font-family: "SF Mono", "Cascadia Code", "Consolas", monospace; font-size: 0.75rem; color: var(--color-text-secondary); }
.empty-text { color: var(--color-text-secondary); font-size: 0.8125rem; }

.type-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 20px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.type-badge--call { background: var(--color-positive-bg); color: var(--color-positive); }
.type-badge--put { background: var(--color-negative-bg); color: var(--color-negative); }
.direction-badge {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  margin-left: 0.35rem;
}
</style>
