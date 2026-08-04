<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as echarts from 'echarts'
import type { ScenarioSweepResponse, SweepStepResult } from '@/types/scenario'
import type { CcyPairOptionMetrics } from '@/types/portfolio'
import { SWEEP_VARIABLE_LABELS } from '@/types/scenario'
import { fmt, toWan } from '@/utils/format'

const props = defineProps<{
  result: ScenarioSweepResponse
}>()

const variableLabel = computed(() => SWEEP_VARIABLE_LABELS[props.result.variable] || props.result.variable)

// ── Greek metrics charts ──────────────────────────────────────────

const greekMetrics = ['delta', 'gamma', 'theta', 'vega'] as const
const greekLabels: Record<string, string> = {
  delta: 'Delta', gamma: 'Gamma', theta: 'Theta (per day)', vega: 'Vega (per 1% vol)',
}

const greekChartRefs = ref<Record<string, HTMLDivElement | null>>({})
const greekCharts = ref<Record<string, echarts.ECharts>>({})

function buildPairLines(
  results: SweepStepResult[],
  key: 'delta' | 'gamma' | 'theta' | 'vega',
): { pairs: string[]; series: echarts.SeriesOption[] } {
  const allPairs = new Set<string>()
  for (const r of results) {
    for (const m of r.summary.option_metrics_by_ccy_pair) {
      if (Math.abs(m[key] ?? 0) > 1e-12) allPairs.add(m.ccy_pair)
    }
  }
  const pairs = Array.from(allPairs).sort()
  const pairMap: Record<string, number[]> = {}
  for (const p of pairs) pairMap[p] = []

  for (const r of results) {
    const seen = new Set<string>()
    for (const m of r.summary.option_metrics_by_ccy_pair) {
      pairMap[m.ccy_pair]?.push(m[key] ?? 0)
      seen.add(m.ccy_pair)
    }
    for (const p of pairs) {
      if (!seen.has(p)) pairMap[p].push(0)
    }
  }

  const colors = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']
  const series: echarts.SeriesOption[] = pairs.map((pair, i) => ({
    name: pair,
    type: 'line' as const,
    data: pairMap[pair],
    smooth: true,
    symbol: 'none' as const,
    lineStyle: { width: 2, color: colors[i % colors.length] },
    itemStyle: { color: colors[i % colors.length] },
  }))

  return { pairs, series }
}

function makeGreekOption(
  key: 'delta' | 'gamma' | 'theta' | 'vega',
  results: SweepStepResult[],
): echarts.EChartsOption {
  const { series } = buildPairLines(results, key)
  if (series.length === 0) return {}

  return {
    tooltip: {
      trigger: 'axis' as const,
      valueFormatter: (v: unknown) => fmt(toWan(typeof v === 'number' ? v : null)) + ' 万',
    },
    legend: {
      data: series.map((s) => s.name as string),
      top: 0,
      textStyle: { fontSize: 10 },
    },
    grid: { left: 70, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'category' as const,
      data: props.result.sweep_points.map((v) => v.toFixed(4)),
      axisLabel: { fontSize: 9, rotate: 10, interval: Math.max(1, Math.floor(props.result.sweep_points.length / 8)) },
    },
    yAxis: {
      type: 'value' as const,
      name: greekLabels[key] + ' (万)',
      nameTextStyle: { fontSize: 10 },
      axisLabel: {
        formatter: (v: number) => fmt(toWan(v), 2) + 'W',
      },
      splitLine: { lineStyle: { type: 'dashed' as const } },
    },
    series,
  }
}

// ── P&L charts ─────────────────────────────────────────────────────

const pnlMetrics = ['total_option_pnl_cny', 'total_spot_pnl_cny', 'total_swap_pnl_cny', 'total_pnl_cny'] as const
const pnlLabels: Record<string, string> = {
  total_option_pnl_cny: '期权总损益 (CNY)', total_spot_pnl_cny: '即期总损益 (CNY)',
  total_swap_pnl_cny: '掉期总损益 (CNY)', total_pnl_cny: '总损益 (CNY)',
}

const pnlChartRefs = ref<Record<string, HTMLDivElement | null>>({})
const pnlCharts = ref<Record<string, echarts.ECharts>>({})

function makePnlOption(
  key: 'total_option_pnl_cny' | 'total_spot_pnl_cny' | 'total_swap_pnl_cny' | 'total_pnl_cny',
  results: SweepStepResult[],
): echarts.EChartsOption {
  const values = results.map((r) => r.summary[key] ?? 0)
  return {
    tooltip: {
      trigger: 'axis' as const,
      valueFormatter: (v: unknown) => {
        const n = typeof v === 'number' ? v : 0
        const abs = Math.abs(n)
        return abs >= 1e4 ? (n / 1e4).toFixed(2) + ' 万' : n.toFixed(2)
      },
    },
    grid: { left: 70, right: 20, top: 10, bottom: 30 },
    xAxis: {
      type: 'category' as const,
      data: props.result.sweep_points.map((v) => v.toFixed(4)),
      axisLabel: { fontSize: 9, rotate: 10, interval: Math.max(1, Math.floor(props.result.sweep_points.length / 8)) },
    },
    yAxis: {
      type: 'value' as const,
      name: 'CNY',
      nameTextStyle: { fontSize: 10 },
      axisLabel: {
        formatter: (v: number) => (v / 1e4).toFixed(0) + 'W',
      },
      splitLine: { lineStyle: { type: 'dashed' as const } },
    },
    series: [{
      type: 'line' as const,
      data: values,
      smooth: true,
      symbol: 'none' as const,
      lineStyle: { width: 2, color: '#3b82f6' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59,130,246,0.25)' },
          { offset: 1, color: 'rgba(59,130,246,0.02)' },
        ]),
      },
    }],
  }
}

// ── Option P&L per pair chart ─────────────────────────────────────

const optPnlChartRef = ref<HTMLDivElement | null>(null)
let optPnlChart: echarts.ECharts | null = null

function makeOptionPnlOption(results: SweepStepResult[]): echarts.EChartsOption {
  const allPairs = new Set<string>()
  for (const r of results) {
    for (const m of r.summary.option_metrics_by_ccy_pair) {
      if (Math.abs(m.total_option_pnl_cny ?? 0) > 1e-12) allPairs.add(m.ccy_pair)
    }
  }
  const pairs = Array.from(allPairs).sort()
  const pairMap: Record<string, number[]> = {}
  for (const p of pairs) pairMap[p] = []

  for (const r of results) {
    const seen = new Set<string>()
    for (const m of r.summary.option_metrics_by_ccy_pair) {
      pairMap[m.ccy_pair]?.push(m.total_option_pnl_cny ?? 0)
      seen.add(m.ccy_pair)
    }
    for (const p of pairs) {
      if (!seen.has(p)) pairMap[p].push(0)
    }
  }

  const colors = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']
  const series: echarts.SeriesOption[] = pairs.map((pair, i) => ({
    name: pair,
    type: 'line' as const,
    data: pairMap[pair],
    smooth: true,
    symbol: 'none' as const,
    lineStyle: { width: 2, color: colors[i % colors.length] },
    itemStyle: { color: colors[i % colors.length] },
  }))

  return {
    tooltip: {
      trigger: 'axis' as const,
      valueFormatter: (v: unknown) => {
        const n = typeof v === 'number' ? v : 0
        const abs = Math.abs(n)
        return abs >= 1e4 ? (n / 1e4).toFixed(2) + ' 万' : n.toFixed(2)
      },
    },
    legend: {
      data: pairs, top: 0, textStyle: { fontSize: 10 },
    },
    grid: { left: 70, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'category' as const,
      data: props.result.sweep_points.map((v) => v.toFixed(4)),
      axisLabel: { fontSize: 9, rotate: 10, interval: Math.max(1, Math.floor(props.result.sweep_points.length / 8)) },
    },
    yAxis: {
      type: 'value' as const,
      name: 'CNY',
      nameTextStyle: { fontSize: 10 },
      axisLabel: { formatter: (v: number) => (v / 1e4).toFixed(0) + 'W' },
      splitLine: { lineStyle: { type: 'dashed' as const } },
    },
    series,
  }
}

// ── Lifecycle ──────────────────────────────────────────────────────

function initCharts() {
  if (!props.result.results || props.result.results.length === 0) return

  for (const key of greekMetrics) {
    const el = greekChartRefs.value[key]
    if (!el) continue
    const old = greekCharts.value[key]
    if (old) old.dispose()
    const chart = echarts.init(el)
    chart.setOption(makeGreekOption(key, props.result.results), true)
    greekCharts.value[key] = chart
  }

  for (const key of pnlMetrics) {
    const el = pnlChartRefs.value[key]
    if (!el) continue
    const old = pnlCharts.value[key]
    if (old) old.dispose()
    const chart = echarts.init(el)
    chart.setOption(makePnlOption(key, props.result.results), true)
    pnlCharts.value[key] = chart
  }

  if (optPnlChartRef.value) {
    if (optPnlChart) optPnlChart.dispose()
    optPnlChart = echarts.init(optPnlChartRef.value)
    optPnlChart.setOption(makeOptionPnlOption(props.result.results), true)
  }
}

function handleResize() {
  for (const chart of Object.values(greekCharts.value)) chart?.resize()
  for (const chart of Object.values(pnlCharts.value)) chart?.resize()
  optPnlChart?.resize()
}

onMounted(() => {
  initCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  for (const chart of Object.values(greekCharts.value)) chart?.dispose()
  for (const chart of Object.values(pnlCharts.value)) chart?.dispose()
  optPnlChart?.dispose()
})

watch(() => props.result, () => {
  initCharts()
}, { deep: true })
</script>

<template>
  <div class="card">
    <div class="header-row">
      <h3>自定义情景分析结果</h3>
      <span class="meta">{{ result.ccy_pair }} — {{ variableLabel }}</span>
    </div>

    <p v-if="!result.results || result.results.length === 0" class="empty-text">
      无数据
    </p>

    <template v-else>
      <!-- Greek metrics per currency pair -->
      <div class="chart-section">
        <h4 class="section-label">期权风险指标 (按货币对)</h4>
        <div class="chart-grid">
          <div
            v-for="key in greekMetrics"
            :key="key"
            class="chart-panel"
          >
            <h5 class="chart-title">{{ greekLabels[key] }}</h5>
            <div :ref="(el: unknown) => { greekChartRefs[key] = el as HTMLDivElement | null }" class="chart-canvas"></div>
          </div>
        </div>
      </div>

      <!-- Per-pair option P&L -->
      <div class="chart-section">
        <h4 class="section-label">期权损益 (按货币对)</h4>
        <div class="chart-panel chart-panel--full">
          <div ref="optPnlChartRef" class="chart-canvas"></div>
        </div>
      </div>

      <!-- Portfolio-level P&L -->
      <div class="chart-section">
        <h4 class="section-label">组合损益指标</h4>
        <div class="chart-grid">
          <div
            v-for="key in pnlMetrics"
            :key="key"
            class="chart-panel"
          >
            <h5 class="chart-title">{{ pnlLabels[key] }}</h5>
            <div :ref="(el: unknown) => { pnlChartRefs[key] = el as HTMLDivElement | null }" class="chart-canvas"></div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-sm);
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}
.header-row h3 {
  font-size: 0.9375rem;
}
.meta {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}
.empty-text {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  font-style: italic;
}
.chart-section {
  margin-top: 0.75rem;
}
.section-label {
  font-size: 0.8125rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--color-text);
}
.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.chart-panel {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 0.4rem;
}
.chart-panel--full {
  grid-column: 1 / -1;
}
.chart-title {
  font-size: 0.6875rem;
  color: var(--color-text-secondary);
  margin: 0 0 0.15rem 0;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.chart-canvas {
  width: 100%;
  height: 240px;
}
</style>
