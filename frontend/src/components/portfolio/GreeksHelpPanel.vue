<script setup lang="ts">
import { ref } from 'vue'

const expanded = ref(false)
</script>

<template>
  <div class="help-card">
    <div class="help-header" @click="expanded = !expanded">
      <span class="help-title">Greeks 计算说明</span>
      <span class="help-toggle">{{ expanded ? '收起' : '展开' }}</span>
    </div>
    <div v-show="expanded" class="help-body">
      <section>
        <h4>逐笔 Greeks（单位量）</h4>
        <p class="help-desc">
          由 QuantLib <code>AnalyticEuropeanEngine</code> 计算，对应 <strong>1 unit of notional1</strong> 的敏感度。
        </p>
        <table class="help-table">
          <thead>
            <tr>
              <th>Greek</th>
              <th>含义</th>
              <th>单位</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Delta</strong></td>
              <td>
                Δ = ∂V / ∂S，spot 变动 1 单位时期权价值的变化
              </td>
              <td>ccy2 / 1 ccy1</td>
            </tr>
            <tr>
              <td><strong>Gamma</strong></td>
              <td>
                Γ = ∂²V / ∂S²，spot 变动 1 单位时 Delta 的变化
              </td>
              <td>ccy2 / (1 ccy1)²</td>
            </tr>
            <tr>
              <td><strong>NPV</strong></td>
              <td>理论期权费现值，Long 为正，Short 为负</td>
              <td>ccy2 / 1 ccy1</td>
            </tr>
            <tr>
              <td><strong>期权费</strong></td>
              <td>成交时记录的期权费，按 spot 折算为 ccy2，再除以 notional1（与 NPV 同口径）</td>
              <td>ccy2 / 1 ccy1</td>
            </tr>
            <tr>
              <td><strong>盈利</strong></td>
              <td>
                期权盈利。买入：NPV − 期权费；卖出：期权费 − NPV。
              </td>
              <td>ccy2 / 1 ccy1</td>
            </tr>
          </tbody>
        </table>
        <p class="help-example">
          例：USD/CNY 的 NPV = 0.1 表示每 1 USD 名义本金对应 0.1 CNY 的期权费。
        </p>
      </section>

      <section>
        <h4>Gamma：QuantLib vs Bloomberg</h4>
        <ul>
          <li>QuantLib Gamma：delta 对 <strong>1 单位 spot 变动</strong> 的变化量。</li>
          <li>Bloomberg Gamma：delta 对 <strong>1% spot 变动</strong> 的变化量。</li>
        </ul>
        <div class="formula">
          Gamma<sub>quantlib</sub> = Gamma<sub>bloomberg</sub> × 100 / spot
        </div>
      </section>

      <section>
        <h4>组合汇总（加权，单位：万）</h4>
        <p class="help-desc">
          组合层面为 <strong>名义本金加权求和</strong>，再折算为 <strong>万</strong>。
        </p>
        <div class="formula-list">
          <div class="formula">加权 Delta = Σ (delta<sub>i</sub> × notional1<sub>i</sub>)</div>
          <div class="formula">加权 Gamma = Σ (gamma<sub>i</sub> × notional1<sub>i</sub>)</div>
          <div class="formula">加权 NPV   = Σ (npv<sub>i</sub>   × notional1<sub>i</sub>)</div>
          <div class="formula">加权盈利   = Σ (profit<sub>i</sub> × notional1<sub>i</sub>)</div>
        </div>
        <p class="help-example">
          盈利公式（逐笔，单位与 NPV 相同，ccy2 / 1 ccy1）：<br>
          买入盈利 = NPV − 期权费<br>
          卖出盈利 = 期权费 − NPV<br>
          组合加权盈利 = Σ (盈利<sub>i</sub> × notional1<sub>i</sub>)
        </p>
      </section>

      <section>
        <h4>关系与符号约定</h4>
        <ul>
          <li><strong>逐笔值</strong> = 单位敏感度 / 价格</li>
          <li><strong>汇总值</strong> = 逐笔值 × notional1，跨组合加总</li>
          <li><strong>符号约定</strong>：Long = 正，Short = 负（代码中对 Short 仓位已做取反处理）</li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style scoped>
.help-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}
.help-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 1.25rem;
  cursor: pointer;
  user-select: none;
  background: var(--color-bg);
  transition: background var(--transition-fast);
}
.help-header:hover {
  background: var(--color-bg-hover, rgba(0,0,0,0.02));
}
.help-title {
  font-size: 0.9375rem;
  font-weight: 600;
}
.help-toggle {
  font-size: 0.75rem;
  color: var(--color-primary);
  font-weight: 500;
}
.help-body {
  padding: 1rem 1.25rem 1.25rem;
  font-size: 0.8125rem;
  line-height: 1.6;
}
.help-body section {
  margin-bottom: 1.25rem;
}
.help-body section:last-child {
  margin-bottom: 0;
}
.help-body h4 {
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
  color: var(--color-text);
}
.help-desc {
  color: var(--color-text-secondary);
  margin-bottom: 0.5rem;
}
.help-example {
  color: var(--color-text-secondary);
  font-style: italic;
  margin-top: 0.5rem;
  font-size: 0.75rem;
}
.help-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
  margin-top: 0.5rem;
}
.help-table th,
.help-table td {
  padding: 0.45rem 0.6rem;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}
.help-table th {
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-bg);
}
.help-table td:first-child {
  white-space: nowrap;
}
.formula-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.formula {
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
  background: var(--color-bg);
  padding: 0.45rem 0.65rem;
  border-radius: var(--radius);
  font-size: 0.78rem;
  border: 1px solid var(--color-border);
  color: var(--color-text);
}
.help-body ul {
  margin: 0.35rem 0 0.5rem;
  padding-left: 1.25rem;
  color: var(--color-text-secondary);
}
.help-body code {
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
  background: var(--color-bg);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-size: 0.75rem;
  border: 1px solid var(--color-border);
}
</style>
