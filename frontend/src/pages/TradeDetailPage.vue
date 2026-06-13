<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTradeStore } from '@/stores/tradeStore'
import { formatDate, formatNumber } from '@/utils/format'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()
const store = useTradeStore()

onMounted(async () => {
  const id = Number(route.params.id)
  if (id) await store.loadTrade(id)
})

function goBack() { router.push('/trades') }
</script>

<template>
  <div class="trade-detail-page">
    <button class="back-btn" @click="goBack">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
      返回列表
    </button>

    <div v-if="store.loading"><LoadingSpinner message="加载交易详情..." /></div>
    <div v-else-if="store.error" class="error">{{ store.error }}</div>

    <template v-else-if="store.currentTrade">
      <div class="detail-header">
        <h1>{{ store.currentTrade.trade_id }}</h1>
        <div class="detail-badges">
          <span :class="store.currentTrade.trade_type === 'CALL' ? 'badge-call' : 'badge-put'">
            {{ store.currentTrade.trade_type }}
          </span>
          <span class="badge-direction">{{ store.currentTrade.direction }}</span>
          <span class="badge-ccy">{{ store.currentTrade.ccy_pair }}</span>
        </div>
      </div>

      <!-- Key fields grid -->
      <div class="detail-grid">
        <div class="detail-section">
          <h3>基本信息</h3>
          <dl>
            <dt>成交编号</dt><dd>{{ store.currentTrade.trade_id }}</dd>
            <dt>来源编号</dt><dd>{{ store.currentTrade.source_trade_id || '--' }}</dd>
            <dt>货币对</dt><dd>{{ store.currentTrade.ccy_pair }}</dd>
            <dt>期权类型</dt><dd>{{ store.currentTrade.option_type || '--' }}</dd>
            <dt>交易类型</dt><dd>{{ store.currentTrade.trade_type }}</dd>
            <dt>方向</dt><dd>{{ store.currentTrade.direction }}</dd>
          </dl>
        </div>

        <div class="detail-section">
          <h3>交易条款</h3>
          <dl>
            <dt>执行价</dt><dd>{{ formatNumber(store.currentTrade.strike, 4) }}</dd>
            <dt>名义本金1</dt><dd>{{ formatNumber(store.currentTrade.notional1) }}</dd>
            <dt>名义本金2</dt><dd>{{ formatNumber(store.currentTrade.notional2) }}</dd>
            <dt>即期汇率</dt><dd>{{ formatNumber(store.currentTrade.spot_rate, 4) }}</dd>
            <dt>波动率</dt><dd>{{ store.currentTrade.volatility !== null ? (store.currentTrade.volatility! * 100).toFixed(2) + '%' : '--' }}</dd>
          </dl>
        </div>

        <div class="detail-section">
          <h3>日期</h3>
          <dl>
            <dt>交易日</dt><dd>{{ formatDate(store.currentTrade.trade_date) }}</dd>
            <dt>到期日</dt><dd>{{ formatDate(store.currentTrade.expiry_date) }}</dd>
            <dt>交割日</dt><dd>{{ formatDate(store.currentTrade.delivery_date) }}</dd>
            <dt>期权费支付日</dt><dd>{{ formatDate(store.currentTrade.premium_payment_date) }}</dd>
            <dt>期限</dt><dd>{{ store.currentTrade.tenor || '--' }}</dd>
          </dl>
        </div>

        <div class="detail-section">
          <h3>期权费</h3>
          <dl>
            <dt>期权费类型</dt><dd>{{ store.currentTrade.premium_type || '--' }}</dd>
            <dt>期权费率</dt><dd>{{ formatNumber(store.currentTrade.premium_rate, 4) }}</dd>
            <dt>期权费金额</dt><dd>{{ formatNumber(store.currentTrade.premium_amount) }}</dd>
            <dt>期权费货币</dt><dd>{{ store.currentTrade.premium_currency || '--' }}</dd>
          </dl>
        </div>

        <div class="detail-section">
          <h3>状态 & 对手方</h3>
          <dl>
            <dt>行权状态</dt><dd>{{ store.currentTrade.exercise_status || '--' }}</dd>
            <dt>交割状态</dt><dd>{{ store.currentTrade.delivery_status || '--' }}</dd>
            <dt>对手方</dt><dd>{{ store.currentTrade.counterparty_name || '--' }}</dd>
            <dt>交易场所</dt><dd>{{ store.currentTrade.venue || '--' }}</dd>
            <dt>清算方式</dt><dd>{{ store.currentTrade.clearing_method || '--' }}</dd>
          </dl>
        </div>
      </div>

      <!-- Greeks section placeholder -->
      <div class="card greeks-card">
        <h3>风险指标 (Greeks)</h3>
        <p class="placeholder-text">Greeks 计算功能将在 Phase 3 实现。届时此处将展示 Delta, Gamma, Vega, Theta, Rho 等风险指标。</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.detail-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.detail-header h1 { margin-bottom: 0; }
.detail-badges { display: flex; gap: 0.5rem; align-items: center; }
.badge-call {
  background: var(--color-positive-bg);
  color: var(--color-positive);
  padding: 3px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge-put {
  background: var(--color-negative-bg);
  color: var(--color-negative);
  padding: 3px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge-direction {
  background: var(--color-primary-bg);
  color: var(--color-primary);
  padding: 3px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge-ccy {
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  padding: 3px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 500;
}
.back-btn {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 0.4rem 0.85rem;
  cursor: pointer;
  margin-bottom: 1.25rem;
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-fast);
}
.back-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  box-shadow: var(--shadow-md);
}
.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}
.detail-section {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition);
}
.detail-section:hover { box-shadow: var(--shadow-md); }
.detail-section h3 {
  font-size: 0.8125rem;
  margin-bottom: 0.75rem;
  color: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.detail-section dl {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 0.35rem 0.5rem;
  font-size: 0.8125rem;
}
.detail-section dt { color: var(--color-text-secondary); }
.detail-section dd { font-weight: 500; }
.card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  box-shadow: var(--shadow-sm);
}
.placeholder-text { font-size: 0.8125rem; color: var(--color-text-secondary); font-style: italic; }
.error { color: var(--color-negative); }
</style>
