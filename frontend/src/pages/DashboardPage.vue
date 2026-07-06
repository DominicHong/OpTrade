<script setup lang="ts">
import { onMounted } from 'vue'
import { useDashboardStore } from '@/stores/dashboardStore'
import { useCurveStore } from '@/stores/curveStore'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import AggregatedResultPanel from '@/components/portfolio/AggregatedResultPanel.vue'

const store = useDashboardStore()
const curveStore = useCurveStore()

onMounted(async () => {
  await curveStore.init()
  await store.init()
})
</script>

<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h1>仪表盘</h1>
      <p class="page-desc">期权交易与风险概览</p>
    </div>

    <!-- Stats Cards -->
    <div class="stats-row">
      <div class="stat-card stat-card--primary">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ store.summary?.option_trade_count ?? '—' }}</span>
          <span class="stat-label">期权交易笔数</span>
        </div>
      </div>
      <div class="stat-card stat-card--blue">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ store.summary?.spot_trade_count ?? '—' }}</span>
          <span class="stat-label">即期交易笔数</span>
        </div>
      </div>
      <div class="stat-card stat-card--amber">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4"/></svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ store.summary?.swap_trade_count ?? '—' }}</span>
          <span class="stat-label">掉期交易笔数</span>
        </div>
      </div>
      <div class="stat-card stat-card--teal">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ store.summary?.total_portfolios ?? '—' }}</span>
          <span class="stat-label">投资组合数</span>
        </div>
      </div>
      <div class="stat-card stat-card--indigo">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ store.summary?.total_counterparties ?? '—' }}</span>
          <span class="stat-label">交易对手</span>
        </div>
      </div>
    </div>

    <!-- Analysis Controls -->
    <div class="card analysis-controls">
      <div class="controls-row">
        <div class="control-group">
          <label for="dash-start-date">起始日</label>
          <input
            id="dash-start-date"
            type="date"
            :value="store.startDate"
            @input="store.startDate = ($event.target as HTMLInputElement).value"
          />
        </div>
        <div class="control-group">
          <label for="dash-end-date">结束日/估值日</label>
          <input
            id="dash-end-date"
            type="date"
            :value="store.valuationDate"
            @input="store.valuationDate = ($event.target as HTMLInputElement).value"
          />
        </div>
        <div class="control-group">
          <label for="dash-curve">参考曲线</label>
          <select
            id="dash-curve"
            :value="store.curveType"
            @change="store.curveType = ($event.target as HTMLSelectElement).value"
          >
            <option v-for="def in curveStore.definitions" :key="def.id" :value="def.curve_type">
              {{ def.name }}
            </option>
          </select>
        </div>
        <div class="control-group control-group--button">
          <button
            class="btn-recalc"
            :disabled="store.loading"
            @click="store.calculate()"
          >
            {{ store.loading ? '计算中...' : '重新计算' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-if="store.error" class="card card-error">
      <p class="error-text">{{ store.error }}</p>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="card">
      <LoadingSpinner message="正在计算组合分析结果..." />
    </div>

    <!-- Results -->
    <AggregatedResultPanel
      v-else-if="store.analysisResult"
      :result="store.analysisResult"
    />

    <!-- Empty state (no calculation yet and not loading) -->
    <div v-else class="card">
      <p class="placeholder-text">点击"重新计算"查看组合分析结果。</p>
    </div>
  </div>
</template>

<style scoped>
.dashboard-page { padding: 1rem; }
.page-header { margin-bottom: 1.5rem; }
.page-desc { color: var(--color-text-secondary); font-size: 0.875rem; margin-top: 0.25rem; }

/* ---- Stats Cards ---- */
.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1rem;
  margin-bottom: 1.25rem;
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
.stat-card--amber::before { background: linear-gradient(90deg, #d97706, #fbbf24); }
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
.stat-card--amber .stat-icon { background: #fffbeb; color: #d97706; }
.stat-card--teal .stat-icon { background: #f0fdfa; color: #0d9488; }
.stat-card--indigo .stat-icon { background: #eef2ff; color: #6366f1; }

.stat-content { display: flex; flex-direction: column; }
.stat-value { display: block; font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; }
.stat-label { display: block; font-size: 0.75rem; color: var(--color-text-secondary); margin-top: 0.15rem; }

/* ---- Analysis Controls ---- */
.card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-sm);
}
.analysis-controls {
  margin-bottom: 1.25rem;
}
.controls-row {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  flex-wrap: wrap;
}
.control-group {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.control-group label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.control-group input,
.control-group select {
  padding: 0.45rem 0.65rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.8125rem;
  background: var(--color-bg);
  color: var(--color-text);
  min-width: 150px;
}
.control-group input:focus,
.control-group select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-bg);
}
.control-group--button {
  justify-content: flex-end;
}
.btn-recalc {
  padding: 0.45rem 1.25rem;
  border: none;
  border-radius: var(--radius);
  background: var(--color-primary);
  color: #fff;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition);
  white-space: nowrap;
}
.btn-recalc:hover:not(:disabled) {
  background: var(--color-primary-dark);
  box-shadow: var(--shadow-md);
}
.btn-recalc:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ---- Error ---- */
.card-error { border-color: #ef4444; }
.error-text { color: #ef4444; font-size: 0.8125rem; }

/* ---- Placeholder ---- */
.placeholder-text {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  font-style: italic;
  text-align: center;
  padding: 2rem 0;
}
</style>
