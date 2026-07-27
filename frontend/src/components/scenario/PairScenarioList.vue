<script setup lang="ts">
import type { EditablePairScenario } from '@/types/scenario'
import PairScenarioControls from './PairScenarioControls.vue'

defineProps<{
  pairParams: Record<string, EditablePairScenario>
}>()

const emit = defineEmits<{
  override: [pair: string, field: 'spot' | 'volatility' | 'rfRateBase' | 'rfRateQuote', value: number | null]
}>()

function onPairOverride(
  pair: string,
  field: 'spot' | 'volatility' | 'rfRateBase' | 'rfRateQuote',
  value: number | null,
) {
  emit('override', pair, field, value)
}
</script>

<template>
  <div class="pair-list">
    <div v-if="Object.keys(pairParams).length === 0" class="empty-state">
      <p>暂无货币对需要设置情景。</p>
      <p class="hint">请先选择投资组合并点击初始化。</p>
    </div>
    <div v-else class="pair-grid">
      <PairScenarioControls
        v-for="pair in Object.values(pairParams)"
        :key="pair.ccyPair"
        :pair="pair"
        @override="(field, val) => onPairOverride(pair.ccyPair, field, val)"
      />
    </div>
  </div>
</template>

<style scoped>
.pair-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}
.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--color-text-secondary);
}
.empty-state p {
  margin: 0;
  font-size: 0.875rem;
}
.hint {
  font-size: 0.75rem;
  opacity: 0.7;
  margin-top: 0.25rem;
}
</style>
