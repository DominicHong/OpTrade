<script setup lang="ts">
import { computed, ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import type { AggregatedSummary } from '@/types/portfolio'

const props = defineProps<{
  summary: AggregatedSummary
}>()

const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const chartOptions = computed(() => {
  const s = props.summary
  if (!s) return {}

  const categories = ['期权总损益', '即期总损益', '掉期总损益', '总损益']
  const values = [
    s.total_option_pnl_cny ?? 0,
    s.total_spot_pnl_cny ?? 0,
    s.total_swap_pnl_cny ?? 0,
    s.total_pnl_cny ?? 0,
  ]

  return {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      valueFormatter: (value: number) => {
        const abs = Math.abs(value)
        if (abs >= 1e8) return (value / 1e8).toFixed(2) + ' 亿 CNY'
        if (abs >= 1e4) return (value / 1e4).toFixed(2) + ' 万 CNY'
        return value.toFixed(2) + ' CNY'
      },
    },
    grid: { left: 70, right: 20, top: 10, bottom: 40 },
    xAxis: {
      type: 'category' as const,
      data: categories,
      axisLabel: { fontSize: 10 },
    },
    yAxis: {
      type: 'value' as const,
      name: 'CNY 万',
      nameTextStyle: { fontSize: 10 },
      axisLabel: {
        formatter: (v: number) => (v / 1e4).toFixed(0) + 'W',
      },
    },
    series: [
      {
        type: 'bar' as const,
        data: values.map((v) => ({
          value: v,
          itemStyle: {
            color: v >= 0 ? '#22c55e' : '#ef4444',
            borderRadius: [4, 4, 0, 0],
          },
        })),
        barMaxWidth: 60,
        label: {
          show: true,
          position: 'top' as const,
          formatter: (params: unknown) => {
            const p = params as { value: number }
            const val = p.value
            const abs = Math.abs(val)
            if (abs >= 1e4) return (val / 1e4).toFixed(1) + 'W'
            return val.toFixed(0)
          },
          fontSize: 10,
        },
      },
    ] as echarts.SeriesOption[],
  }
})

function renderChart() {
  if (!chartRef.value || !chart) return
  chart.setOption(chartOptions.value, true)
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

watch(() => props.summary, () => renderChart(), { deep: true })
</script>

<template>
  <div class="bar-chart-wrapper">
    <div ref="chartRef" class="chart-canvas"></div>
  </div>
</template>

<style scoped>
.bar-chart-wrapper {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 0.75rem;
  box-shadow: var(--shadow-sm);
}
.chart-canvas {
  width: 100%;
  height: 250px;
}
</style>
