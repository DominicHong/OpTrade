<script setup lang="ts">
import { computed, ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import type { CcyPairOptionMetrics } from '@/types/portfolio'
import { fmt, profitColor } from '@/utils/format'

const props = defineProps<{
  metrics: CcyPairOptionMetrics[]
}>()

const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const showCny = ref(true)

const chartOptions = computed(() => {
  if (!props.metrics || props.metrics.length === 0) return {}

  const pairs = props.metrics.map((m) => m.ccy_pair)
  const totalOptionPnl = props.metrics.map((m) => showCny.value ? m.total_option_pnl_cny : m.total_option_pnl_cny)
  const npv = props.metrics.map((m) => showCny.value ? m.npv_cny : m.npv_cny)
  const premiumPnl = props.metrics.map((m) => showCny.value ? m.premium_pnl_cny : m.premium_pnl_cny)
  const exercisePnl = props.metrics.map((m) => showCny.value ? m.exercise_pnl_cny : m.exercise_pnl_cny)
  const delta = props.metrics.map((m) => m.delta)
  const gamma = props.metrics.map((m) => m.gamma)
  const theta = props.metrics.map((m) => m.theta)
  const vega = props.metrics.map((m) => m.vega)

  return {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      valueFormatter: (value: number) => {
        const abs = Math.abs(value)
        if (abs >= 1e8) return (value / 1e8).toFixed(2) + ' 亿'
        if (abs >= 1e4) return (value / 1e4).toFixed(2) + ' 万'
        return value.toFixed(2)
      },
    },
    legend: {
      data: [showCny.value ? '损益(CNY)' : '损益', 'Delta', 'Gamma', 'Theta', 'Vega'],
      top: 0,
      textStyle: { fontSize: 11 },
    },
    grid: { left: 60, right: 20, top: 35, bottom: 50 },
    xAxis: {
      type: 'category' as const,
      data: pairs,
      axisLabel: { rotate: pairs.length > 3 ? 25 : 0, fontSize: 10 },
    },
    yAxis: [
      {
        type: 'value' as const,
        name: showCny.value ? 'CNY 万' : '原币',
        nameTextStyle: { fontSize: 10 },
        axisLabel: {
          formatter: (v: number) => (v / 1e4).toFixed(0) + 'W',
        },
        splitLine: { lineStyle: { type: 'dashed' as const } },
      },
      {
        type: 'value' as const,
        name: 'Greek',
        nameTextStyle: { fontSize: 10 },
        axisLabel: { fontSize: 9 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: showCny.value ? '损益(CNY)' : '损益',
        type: 'bar' as const,
        data: totalOptionPnl.map((v, i) => ({
          value: v,
          itemStyle: {
            color: v >= 0 ? '#22c55e' : '#ef4444',
          },
        })),
        barMaxWidth: 30,
      },
      {
        name: 'Delta',
        type: 'bar' as const,
        yAxisIndex: 1,
        data: delta,
        barMaxWidth: 30,
        itemStyle: { color: '#3b82f6' },
      },
      {
        name: 'Gamma',
        type: 'bar' as const,
        yAxisIndex: 1,
        data: gamma,
        barMaxWidth: 30,
        itemStyle: { color: '#8b5cf6' },
      },
      {
        name: 'Theta',
        type: 'bar' as const,
        yAxisIndex: 1,
        data: theta,
        barMaxWidth: 30,
        itemStyle: { color: '#f59e0b' },
      },
      {
        name: 'Vega',
        type: 'bar' as const,
        yAxisIndex: 1,
        data: vega,
        barMaxWidth: 30,
        itemStyle: { color: '#ec4899' },
      },
    ] as echarts.SeriesOption[],
  }
})

function renderChart() {
  if (!chartRef.value || !chart) return
  const opts = chartOptions.value
  if (!opts || !opts.series) return
  chart.setOption(opts, true)
}

function handleResize() {
  chart?.resize()
}

onMounted(() => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  renderChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})

watch(() => [props.metrics, showCny.value], () => {
  renderChart()
}, { deep: true })
</script>

<template>
  <div class="bar-chart-wrapper">
    <div class="chart-header">
      <label class="toggle-label">
        <input type="checkbox" v-model="showCny" />
        显示 CNY
      </label>
    </div>
    <div ref="chartRef" class="chart-canvas"></div>
    <div v-if="!metrics || metrics.length === 0" class="empty-overlay">无数据</div>
  </div>
</template>

<style scoped>
.bar-chart-wrapper {
  position: relative;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 0.75rem;
  box-shadow: var(--shadow-sm);
}
.chart-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 0.25rem;
}
.toggle-label {
  font-size: 0.6875rem;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  gap: 0.25rem;
  cursor: pointer;
}
.chart-canvas {
  width: 100%;
  height: 320px;
}
.empty-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}
</style>
