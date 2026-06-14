<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { fetchPortfolioGreeks } from '@/api/portfolios'
import { toWan } from '@/utils/format'
import type { PortfolioGreeksResponse } from '@/types/portfolio'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'

const pfStore = usePortfolioStore()

// Greeks parameters
const riskFreeRate = ref(3)
const volatility = ref<number | null>(null)
const spot = ref<number | null>(null)
const valuationDate = ref(new Date().toISOString().slice(0, 10))

// Greeks results
const greeksResult = ref<PortfolioGreeksResponse | null>(null)
const greeksLoading = ref(false)
const greeksError = ref<string | null>(null)

onMounted(async () => {
  await pfStore.loadPortfolios()
})

// Recalculate when portfolio changes
watch(() => pfStore.currentPortfolio, (newVal) => {
  greeksResult.value = null
  greeksError.value = null
})

async function calculateGreeks() {
  if (!pfStore.currentPortfolio) return
  greeksLoading.value = true
  greeksError.value = null
  try {
    greeksResult.value = await fetchPortfolioGreeks(pfStore.currentPortfolio.id, {
      risk_free_rate: riskFreeRate.value / 100,
      volatility: volatility.value,
      spot: spot.value,
      valuation_date: valuationDate.value,
    })
  } catch (e: unknown) {
    greeksError.value = e instanceof Error ? e.message : 'Greeks 计算失败'
  } finally {
    greeksLoading.value = false
  }
}

function fmt(val: number | null | undefined, decimals = 4): string {
  if (val == null) return '—'
  return val.toFixed(decimals)
}
</script>

<template>
  <div class="portfolio-page">
    <div class="page-header">
      <h1>组合分析</h1>
      <p class="page-desc">选择投资组合以查看聚合风险指标和敞口分析</p>
    </div>

    <div v-if="pfStore.loading"><LoadingSpinner message="加载组合..." /></div>

    <template v-else>
      <!-- Portfolio selector -->
      <div class="card">
        <h3>投资组合</h3>
        <div v-if="pfStore.portfolios.length === 0" class="placeholder-text">暂无投资组合。导入交易数据后将自动创建。</div>
        <div v-else class="portfolio-list">
          <div
            v-for="p in pfStore.portfolios"
            :key="p.id"
            class="portfolio-item"
            :class="{ active: pfStore.currentPortfolio?.id === p.id }"
            @click="pfStore.loadPortfolio(p.id)"
          >
            <div class="pf-info">
              <span class="pf-name">{{ p.name }}</span>
              <span class="pf-count">{{ p.trade_count }} 笔交易</span>
            </div>
            <svg v-if="pfStore.currentPortfolio?.id === p.id" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg>
          </div>
        </div>
      </div>

      <!-- Parameters & Calculate -->
      <div class="card" v-if="pfStore.currentPortfolio">
        <h3>计算参数</h3>
        <div class="params-grid">
          <div class="param-field">
            <label for="valuation-date">估值日期</label>
            <input id="valuation-date" type="date" v-model="valuationDate" />
          </div>
          <div class="param-field">
            <label for="risk-free-rate">无风险利率 (%)</label>
            <input id="risk-free-rate" type="number" step="0.1" v-model.number="riskFreeRate" placeholder="3" />
          </div>
          <div class="param-field">
            <label for="volatility">波动率</label>
            <input id="volatility" type="number" step="0.001" v-model.number="volatility" placeholder="留空则使用交易自带波动率" />
          </div>
          <div class="param-field">
            <label for="spot">即期汇率</label>
            <input id="spot" type="number" step="0.0001" v-model.number="spot" placeholder="留空则使用交易自带即期" />
          </div>
        </div>
        <button class="btn-calc" @click="calculateGreeks" :disabled="greeksLoading">
          {{ greeksLoading ? '计算中...' : '计算 Greeks' }}
        </button>
      </div>

      <!-- Aggregated Greeks -->
      <div class="card" v-if="greeksResult">
        <h3>{{ greeksResult.portfolio_name }} — 聚合风险指标</h3>
        <div class="greeks-summary">
          <div class="greek-card greek-delta">
            <span class="greek-label">Delta (加权, 万)</span>
            <span class="greek-value">{{ fmt(toWan(greeksResult.total_delta), 2) }}</span>
          </div>
          <div class="greek-card greek-gamma">
            <span class="greek-label">Gamma (加权, 万)</span>
            <span class="greek-value">{{ fmt(toWan(greeksResult.total_gamma), 2) }}</span>
          </div>
          <div class="greek-card greek-npv">
            <span class="greek-label">NPV (加权, 万)</span>
            <span class="greek-value">{{ fmt(toWan(greeksResult.total_npv), 2) }}</span>
          </div>
        </div>
        <div class="params-used">
          <span>参数: r = {{ (greeksResult.risk_free_rate * 100).toFixed(2) }}%, vol = {{ greeksResult.volatility_used ?? '交易自带' }}, spot = {{ greeksResult.spot_used ?? '交易自带' }}</span>
        </div>
      </div>

      <!-- Error -->
      <div class="card card-error" v-if="greeksError">
        <p class="error-text">{{ greeksError }}</p>
      </div>

      <!-- Trade-level breakdown -->
      <div class="card" v-if="greeksResult && greeksResult.trades.length > 0">
        <h3>逐笔明细</h3>
        <div class="table-wrap">
          <table class="greeks-table">
            <thead>
              <tr>
                <th>交易ID</th>
                <th>货币对</th>
                <th>类型</th>
                <th>方向</th>
                <th>Strike</th>
                <th>Notional(万)</th>
                <th>Delta</th>
                <th>Gamma</th>
                <th>NPV</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in greeksResult.trades" :key="t.trade_id" :class="{ 'row-error': t.error }">
                <td>{{ t.trade_id_str ?? t.trade_id }}</td>
                <td>{{ t.ccy_pair ?? '—' }}</td>
                <td>{{ t.option_type ?? '—' }}</td>
                <td>{{ t.direction ?? '—' }}</td>
                <td>{{ fmt(t.strike) }}</td>
                <td>{{ fmt(toWan(t.notional1), 2) }}</td>
                <td>{{ t.error ? '—' : fmt(t.delta) }}</td>
                <td>{{ t.error ? '—' : fmt(t.gamma) }}</td>
                <td>{{ t.error ? '—' : fmt(t.npv, 2) }}</td>
              </tr>
              <tr v-for="t in greeksResult.trades" :key="'err-' + t.trade_id" class="error-row-detail" v-show="t.error">
                <td colspan="9" class="error-inline">{{ t.error }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page-header { margin-bottom: 1.5rem; }
.page-desc { color: var(--color-text-secondary); font-size: 0.875rem; margin-top: 0.25rem; }
.card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-sm);
}
.card h3 { font-size: 0.9375rem; margin-bottom: 0.85rem; }
.placeholder-text { font-size: 0.8125rem; color: var(--color-text-secondary); font-style: italic; }
.portfolio-list { display: flex; flex-wrap: wrap; gap: 0.65rem; }
.portfolio-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 0.8125rem;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
}
.portfolio-item:hover {
  border-color: var(--color-primary-lighter);
  box-shadow: var(--shadow-md);
}
.portfolio-item.active {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
  box-shadow: var(--shadow-blue);
}
.pf-info { display: flex; flex-direction: column; gap: 0.1rem; }
.pf-name { font-weight: 600; }
.pf-count { font-size: 0.7rem; color: var(--color-text-secondary); }
.portfolio-item.active svg { color: var(--color-primary); }

/* Params */
.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}
.param-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.param-field label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-weight: 500;
}
.param-field input {
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.8125rem;
  background: var(--color-bg);
  color: var(--color-text);
  transition: border-color var(--transition-fast);
}
.param-field input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-bg);
}
.btn-calc {
  padding: 0.5rem 1.25rem;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.btn-calc:hover { filter: brightness(1.1); }
.btn-calc:disabled { opacity: 0.6; cursor: not-allowed; }

/* Greeks summary */
.greeks-summary {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.85rem;
  margin-bottom: 0.75rem;
}
.greek-card {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.85rem 1rem;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
}
.greek-label {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 600;
}
.greek-value {
  font-size: 1.15rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.greek-delta .greek-value { color: #2563eb; }
.greek-gamma .greek-value { color: #7c3aed; }
.greek-npv .greek-value { color: #059669; }
.params-used {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  font-style: italic;
}

/* Error */
.card-error { border-color: #ef4444; }
.error-text { color: #ef4444; font-size: 0.8125rem; }

/* Table */
.table-wrap { overflow-x: auto; }
.greeks-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}
.greeks-table th,
.greeks-table td {
  padding: 0.5rem 0.65rem;
  text-align: right;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}
.greeks-table th {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-weight: 600;
  background: var(--color-bg);
}
.greeks-table td:first-child,
.greeks-table th:first-child { text-align: left; }
.row-error { color: var(--color-text-secondary); }
.error-inline { color: #ef4444; font-size: 0.75rem; font-style: italic; }
</style>
