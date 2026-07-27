<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import type { BuiltinScenariosResponse } from '@/types/scenario'
import { BUILTIN_SCENARIO_META } from '@/types/scenario'
import type { BuiltinScenarioMeta } from '@/types/scenario'

const props = defineProps<{
  result: BuiltinScenariosResponse
}>()

const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const selectedMetric = ref<'total_option_pnl_cny' | 'total_spot_pnl_cny' | 'total_swap_pnl_cny' | 'total_pnl_cny'>('total_pnl_cny')

const metricLabels: Record<string, string> = {
  total_option_pnl_cny: '期权总损益',
  total_spot_pnl_cny: '即期总损益',
  total_swap_pnl_cny: '掉期总损益',
  total_pnl_cny: '总损益',
}

const allScenarios = computed(() => {
  return [props.result.baseline, ...props.result.scenarios]
})

const metaById = computed(() => {
  const map: Record<string, BuiltinScenarioMeta> = {}
  for (const m of BUILTIN_SCENARIO_META) {
    map[m.id] = m
  }
  return map
})

const chartOptions = computed(() => {
  const labels: string[] = []
  const values: number[] = []
  const descriptions: string[] = []

  for (const s of allScenarios.value) {
    if (!s.scenario_id) continue
    const meta = metaById.value[s.scenario_id]
    labels.push(meta?.name || s.scenario_name || s.scenario_id)
    values.push(s.summary[selectedMetric.value] ?? 0)
    descriptions.push(meta?.description || '')
  }

  return {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      formatter: (params: unknown) => {
        const pArray = params as Array<{ name: string; value: number; dataIndex: number }>
        if (!pArray || pArray.length === 0) return ''
        const p = pArray[0]
        const abs = Math.abs(p.value)
        let valStr: string
        if (abs >= 1e8) valStr = (p.value / 1e8).toFixed(2) + ' 亿 CNY'
        else if (abs >= 1e4) valStr = (p.value / 1e4).toFixed(2) + ' 万 CNY'
        else valStr = p.value.toFixed(2) + ' CNY'
        return `${p.name}<br/>${metricLabels[selectedMetric.value]}: ${valStr}<br/>${descriptions[p.dataIndex] || ''}`
      },
    },
    grid: { left: 80, right: 20, top: 10, bottom: 90 },
    xAxis: {
      type: 'category' as const,
      data: labels,
      axisLabel: {
        rotate: 35,
        fontSize: 9,
        overflow: 'truncate' as const,
        width: 60,
      },
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
        barMaxWidth: 40,
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

watch(() => [props.result, selectedMetric.value], () => renderChart(), { deep: true })
</script>

<template>
  <div class="card">
    <h3>系统内置情景对比</h3>

    <!-- Metric selector -->
    <div class="metric-selector">
      <label v-for="(label, key) in metricLabels" :key="key" class="metric-radio">
        <input type="radio" :value="key" v-model="selectedMetric" />
        <span>{{ label }}</span>
      </label>
    </div>

    <!-- Bar chart -->
    <div ref="chartRef" class="chart-canvas"></div>

    <!-- Table -->
    <div class="table-wrap">
      <table class="scenario-table">
        <thead>
          <tr>
            <th>情景</th>
            <th>描述</th>
            <th class="num-col">期权损益(CNY)</th>
            <th class="num-col">即期损益(CNY)</th>
            <th class="num-col">掉期损益(CNY)</th>
            <th class="num-col">总损益(CNY)</th>
            <th class="num-col">期权笔数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in allScenarios" :key="s.scenario_id || 'unknown'">
            <td class="name-cell">{{ metaById[s.scenario_id || '']?.name || s.scenario_name }}</td>
            <td class="desc-cell">{{ metaById[s.scenario_id || '']?.description || '' }}</td>
            <td class="num-cell" :class="(s.summary.total_option_pnl_cny ?? 0) >= 0 ? 'pos' : 'neg'">
              {{ ((s.summary.total_option_pnl_cny ?? 0) / 1e4).toFixed(2) }}W
            </td>
            <td class="num-cell" :class="(s.summary.total_spot_pnl_cny ?? 0) >= 0 ? 'pos' : 'neg'">
              {{ ((s.summary.total_spot_pnl_cny ?? 0) / 1e4).toFixed(2) }}W
            </td>
            <td class="num-cell" :class="(s.summary.total_swap_pnl_cny ?? 0) >= 0 ? 'pos' : 'neg'">
              {{ ((s.summary.total_swap_pnl_cny ?? 0) / 1e4).toFixed(2) }}W
            </td>
            <td class="num-cell bold" :class="(s.summary.total_pnl_cny ?? 0) >= 0 ? 'pos' : 'neg'">
              {{ ((s.summary.total_pnl_cny ?? 0) / 1e4).toFixed(2) }}W
            </td>
            <td class="num-cell">{{ s.option_trade_count }}</td>
          </tr>
        </tbody>
      </table>
    </div>
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
.card h3 {
  font-size: 0.9375rem;
  margin-bottom: 0.75rem;
}
.metric-selector {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}
.metric-radio {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  cursor: pointer;
}
.metric-radio input {
  accent-color: var(--color-primary);
}
.chart-canvas {
  width: 100%;
  height: 300px;
  margin-bottom: 0.75rem;
}
.table-wrap {
  overflow-x: auto;
}
.scenario-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}
.scenario-table th,
.scenario-table td {
  padding: 0.4rem 0.5rem;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}
.scenario-table th {
  font-size: 0.6875rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: var(--color-bg);
  position: sticky;
  top: 0;
}
.num-col { text-align: right; }
.num-cell { text-align: right; }
.name-cell { font-weight: 500; color: var(--color-primary); }
.desc-cell { font-size: 0.6875rem; color: var(--color-text-secondary); }
.bold { font-weight: 600; }
.pos { color: #22c55e; }
.neg { color: #ef4444; }
</style>
