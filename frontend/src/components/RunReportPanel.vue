<template>
  <div v-if="report" class="report-panel">
    <header class="sum">
      <div>
        <div class="kicker">{{ t('reportUi.detail') }}</div>
        <h3>{{ t('reportUi.summaryTitle') }}</h3>
      </div>
      <div class="chips">
        <span class="chip ok">{{ t('reportUi.passed', { n: summary.passed ?? 0 }) }}</span>
        <span class="chip bad">{{ t('reportUi.failed', { n: summary.failed ?? 0 }) }}</span>
        <span class="chip">{{ t('reportUi.total', { n: summary.total ?? details.length }) }}</span>
        <span class="chip" v-if="summary.time_ms != null">{{ summary.time_ms }}ms</span>
        <ConfidenceBadge v-if="summary.confidence_avg != null" :value="summary.confidence_avg" />
      </div>
    </header>

    <article v-for="(d, i) in details" :key="d.case_id || i" class="case" :class="{ fail: !d.ok }">
      <button class="case-head" type="button" @click="toggle(i)">
        <span class="dot" :class="d.ok ? 'ok' : 'bad'" />
        <strong>{{ d.case_title || d.title || t('reportUi.untitled') }}</strong>
        <code>{{ d.method || d.request?.method }} {{ shortUrl(d) }}</code>
        <span class="meta">{{ d.time_ms ?? '—' }}ms · HTTP {{ d.status_code ?? d.response?.status_code ?? '—' }}</span>
      </button>
      <div v-if="open.has(i)" class="case-body">
        <p v-if="failMessage(d)" class="fail-msg">{{ failMessage(d) }}</p>
        <div class="block-title">{{ t('reportUi.asserts') }}</div>
        <table v-if="(d.assertions || []).length" class="grid">
          <thead>
            <tr>
              <th>{{ t('reportUi.assertName') }}</th>
              <th>{{ t('reportUi.expected') }}</th>
              <th>{{ t('reportUi.actual') }}</th>
              <th>{{ t('common.status') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(a, ai) in d.assertions" :key="ai" :class="{ bad: !a.ok }">
              <td>{{ a.name }}</td>
              <td class="mono">{{ fmt(a.expected) }}</td>
              <td class="mono">{{ fmt(a.actual) }}</td>
              <td>{{ a.ok ? t('reportUi.pass') : a.message || t('reportUi.fail') }}</td>
            </tr>
          </tbody>
        </table>
        <el-empty v-else :description="t('reportUi.noAssert')" :image-size="48" />

        <div class="split">
          <div>
            <div class="block-title">{{ t('reportUi.request') }}</div>
            <pre>{{ fmt(d.request || { method: d.method, url: d.url }) }}</pre>
          </div>
          <div>
            <div class="block-title">{{ t('reportUi.response') }}</div>
            <pre>{{ d.response?.body_preview || d.body_preview || d.error || '—' }}</pre>
          </div>
        </div>

        <div v-if="d.extracted && Object.keys(d.extracted).length">
          <div class="block-title">{{ t('reportUi.extracted') }}</div>
          <pre>{{ fmt(d.extracted) }}</pre>
        </div>
      </div>
    </article>

    <div v-if="variables && Object.keys(variables).length" class="vars">
      <div class="block-title">{{ t('reportUi.finalVars') }}</div>
      <pre>{{ fmt(variables) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import ConfidenceBadge from './ConfidenceBadge.vue'

const props = defineProps<{ report: any }>()
const { t } = useI18n()
const open = ref<Set<number>>(new Set([0]))

const summary = computed(() => props.report?.summary_json || props.report?.summary || {})
const details = computed(() => {
  const d = props.report?.detail_json?.details || props.report?.details || []
  return Array.isArray(d) ? d : []
})
const variables = computed(() => props.report?.detail_json?.variables || props.report?.variables || {})

watch(
  () => props.report?.id,
  () => {
    const firstFail = details.value.findIndex((x: any) => !x.ok)
    open.value = new Set([firstFail >= 0 ? firstFail : 0])
  },
)

function toggle(i: number) {
  const next = new Set(open.value)
  if (next.has(i)) next.delete(i)
  else next.add(i)
  open.value = next
}

function shortUrl(d: any) {
  const u = d.request?.url || d.url || d.request?.path || ''
  return String(u).replace(/^https?:\/\/[^/]+/, '') || '/'
}

function failMessage(d: any) {
  if (d.ok) return ''
  if (d.error) return d.error
  const msgs = (d.assertions || []).filter((a: any) => !a.ok).map((a: any) => a.message).filter(Boolean)
  return msgs.join('；')
}

function fmt(v: any) {
  if (v == null) return '—'
  if (typeof v === 'string') return v
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return String(v)
  }
}
</script>

<style scoped>
.report-panel {
  margin-top: 14px;
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.72);
}
.sum {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}
.kicker {
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--teal-deep);
  font-weight: 650;
}
.sum h3 {
  margin: 4px 0 0;
  font-family: var(--font-brand);
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
}
.chip {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(18, 32, 43, 0.06);
}
.chip.ok {
  color: var(--ok);
  background: rgba(47, 157, 106, 0.12);
}
.chip.bad {
  color: var(--rose);
  background: rgba(196, 91, 91, 0.12);
}
.case {
  border-top: 1px solid var(--line);
}
.case-head {
  width: 100%;
  display: grid;
  grid-template-columns: 14px 1fr auto auto;
  gap: 10px;
  align-items: center;
  padding: 10px 0;
  border: 0;
  background: transparent;
  font: inherit;
  color: inherit;
  text-align: left;
  cursor: pointer;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 99px;
  background: var(--ok);
}
.dot.bad {
  background: var(--rose);
}
code {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--ink-soft);
}
.meta {
  font-size: 12px;
  color: var(--mute);
  white-space: nowrap;
}
.case.fail .case-head strong {
  color: var(--rose);
}
.case-body {
  padding: 0 0 14px 24px;
}
.fail-msg {
  color: var(--rose);
  font-size: 13px;
  margin: 0 0 10px;
}
.block-title {
  font-family: var(--font-brand);
  font-weight: 650;
  margin: 10px 0 6px;
  font-size: 13px;
}
.grid {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.grid th,
.grid td {
  border-bottom: 1px solid var(--line);
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
}
.grid tr.bad td {
  color: var(--rose);
}
.split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
pre {
  margin: 0;
  padding: 10px;
  border-radius: 10px;
  background: rgba(18, 32, 43, 0.04);
  font-family: var(--font-mono);
  font-size: 12px;
  white-space: pre-wrap;
  max-height: 240px;
  overflow: auto;
}
.mono {
  font-family: var(--font-mono);
  word-break: break-all;
}
.vars {
  margin-top: 8px;
  border-top: 1px solid var(--line);
}
@media (max-width: 900px) {
  .split,
  .case-head {
    grid-template-columns: 14px 1fr;
  }
}
</style>
