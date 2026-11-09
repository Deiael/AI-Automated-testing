<template>
  <div v-if="report" class="viewer">
    <header class="sum">
      <div class="kpi">
        <span class="k">{{ t('report.total') }}</span>
        <strong>{{ summary.total ?? details.length }}</strong>
      </div>
      <div class="kpi ok">
        <span class="k">{{ t('report.passed') }}</span>
        <strong>{{ summary.passed ?? '—' }}</strong>
      </div>
      <div class="kpi fail">
        <span class="k">{{ t('report.failed') }}</span>
        <strong>{{ summary.failed ?? '—' }}</strong>
      </div>
      <div class="kpi">
        <span class="k">{{ t('report.time') }}</span>
        <strong>{{ summary.time_ms ?? elapsed }}ms</strong>
      </div>
      <div class="kpi" v-if="summary.confidence_avg != null">
        <span class="k">{{ t('report.confidence') }}</span>
        <ConfidenceBadge :value="summary.confidence_avg" />
      </div>
    </header>

    <div v-if="summary.failed_titles?.length" class="fail-strip">
      {{ t('report.failedList') }}：{{ summary.failed_titles.join(' · ') }}
    </div>

    <article v-for="(row, idx) in details" :key="row.case_id || idx" class="case" :class="{ fail: !row.ok }">
      <button type="button" class="case-head" @click="toggle(idx)">
        <span class="badge" :class="row.ok ? 'ok' : 'bad'">{{ row.ok ? t('report.pass') : t('report.fail') }}</span>
        <strong class="title">{{ row.case_title || row.case_id || `#${idx + 1}` }}</strong>
        <span class="meta">{{ row.method || row.request?.method }} {{ shortUrl(row) }}</span>
        <span class="meta mono">{{ row.status_code ?? row.response?.status_code ?? '—' }} · {{ row.time_ms ?? 0 }}ms</span>
        <ConfidenceBadge v-if="row.confidence != null" :value="row.confidence" />
        <span class="chev">{{ open.has(idx) ? '▾' : '▸' }}</span>
      </button>

      <div v-if="open.has(idx)" class="case-body">
        <div v-if="row.error" class="err">{{ row.error }}</div>

        <div class="block-title">{{ t('report.assertions') }}</div>
        <table class="tbl" v-if="(row.assertions || []).length">
          <thead>
            <tr>
              <th>{{ t('report.assertName') }}</th>
              <th>{{ t('report.assertResult') }}</th>
              <th>{{ t('report.assertExpected') }}</th>
              <th>{{ t('report.assertActual') }}</th>
              <th>{{ t('report.assertMsg') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(a, i) in row.assertions" :key="i" :class="{ bad: !a.ok }">
              <td>{{ a.name }}</td>
              <td>{{ a.ok ? '✓' : '✗' }}</td>
              <td class="mono">{{ fmt(a.expected) }}</td>
              <td class="mono">{{ fmt(a.actual) }}</td>
              <td>{{ a.message || '—' }}</td>
            </tr>
          </tbody>
        </table>
        <el-empty v-else :description="t('report.noAssert')" :image-size="48" />

        <div class="two">
          <div>
            <div class="block-title">{{ t('report.request') }}</div>
            <pre>{{ fmt(row.request || { method: row.method, url: row.url }) }}</pre>
          </div>
          <div>
            <div class="block-title">{{ t('report.response') }}</div>
            <pre>{{ fmt(row.response || { status_code: row.status_code, body_preview: row.body_preview }) }}</pre>
          </div>
        </div>

        <div v-if="row.extracted && Object.keys(row.extracted).length" class="vars">
          <div class="block-title">{{ t('report.extracted') }}</div>
          <pre>{{ fmt(row.extracted) }}</pre>
        </div>
      </div>
    </article>

    <div v-if="variables && Object.keys(variables).length" class="vars panel-soft">
      <div class="block-title">{{ t('report.variables') }}</div>
      <pre>{{ fmt(variables) }}</pre>
    </div>

    <div v-if="mcpLog.length" class="vars panel-soft">
      <div class="block-title">{{ t('report.mcpLog') }} ({{ summary.mcp_calls || mcpLog.length }})</div>
      <article v-for="(m, i) in mcpLog" :key="i" class="mcp-item" :class="{ bad: !m.ok }">
        <strong>{{ m.phase }} · {{ m.tool }}</strong>
        <span class="muted">{{ m.server_name || m.server_id }} · {{ m.case_title || '—' }}</span>
        <pre>{{ fmt(m.error ? { error: m.error, arguments: m.arguments } : { arguments: m.arguments, result: m.result }) }}</pre>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import ConfidenceBadge from './ConfidenceBadge.vue'

const props = defineProps<{ report: any }>()
const { t } = useI18n()
const open = ref<Set<number>>(new Set())

const summary = computed(() => props.report?.summary_json || {})
const details = computed(() => {
  const d = props.report?.detail_json?.details
  return Array.isArray(d) ? d : []
})
const variables = computed(() => props.report?.detail_json?.variables || {})
const mcpLog = computed(() => {
  const list = props.report?.detail_json?.mcp_log
  return Array.isArray(list) ? list : []
})
const elapsed = computed(() => details.value.reduce((acc: number, r: any) => acc + Number(r.time_ms || 0), 0))

watch(
  () => props.report?.id,
  () => {
    open.value = new Set()
    details.value.forEach((r: any, i: number) => {
      if (!r.ok) open.value.add(i)
    })
  },
  { immediate: true },
)

function toggle(i: number) {
  const next = new Set(open.value)
  if (next.has(i)) next.delete(i)
  else next.add(i)
  open.value = next
}

function shortUrl(row: any) {
  const url = row.url || row.request?.url || row.path || ''
  return String(url).replace(/^https?:\/\/[^/]+/, '') || '/'
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
.viewer {
  display: grid;
  gap: 12px;
}
.sum {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.kpi {
  min-width: 88px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.7);
  display: grid;
  gap: 4px;
}
.kpi .k {
  font-size: 11px;
  color: var(--mute);
}
.kpi strong {
  font-family: var(--font-brand);
  font-size: 20px;
}
.kpi.ok strong {
  color: var(--ok);
}
.kpi.fail strong {
  color: var(--rose);
}
.fail-strip {
  padding: 8px 12px;
  border-radius: 10px;
  background: rgba(196, 91, 91, 0.1);
  color: var(--rose);
  font-size: 13px;
}
.case {
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.55);
}
.case.fail {
  border-color: rgba(196, 91, 91, 0.35);
}
.case-head {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  align-items: center;
  padding: 10px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  font: inherit;
  color: inherit;
}
.badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}
.badge.ok {
  background: rgba(47, 157, 106, 0.14);
  color: var(--ok);
}
.badge.bad {
  background: rgba(196, 91, 91, 0.14);
  color: var(--rose);
}
.title {
  font-family: var(--font-brand);
}
.meta {
  font-size: 12px;
  color: var(--mute);
}
.mono {
  font-family: var(--font-mono);
}
.chev {
  margin-left: auto;
  color: var(--mute);
}
.case-body {
  padding: 0 12px 12px;
  border-top: 1px solid var(--line);
}
.err {
  margin: 10px 0;
  color: var(--rose);
  font-size: 13px;
}
.block-title {
  margin: 12px 0 6px;
  font-family: var(--font-brand);
  font-weight: 650;
  font-size: 13px;
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.tbl th,
.tbl td {
  border-bottom: 1px solid var(--line);
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
}
.tbl tr.bad td {
  background: rgba(196, 91, 91, 0.06);
}
.two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
pre {
  margin: 0;
  padding: 10px;
  border-radius: 10px;
  background: rgba(18, 32, 43, 0.04);
  font-family: var(--font-mono);
  font-size: 11px;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 240px;
  overflow: auto;
}
.vars {
  margin-top: 4px;
}
.panel-soft {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(15, 143, 134, 0.04);
}
.mcp-item {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--line);
}
.mcp-item.bad strong {
  color: var(--rose);
}
.mcp-item .muted {
  display: block;
  font-size: 12px;
  color: var(--mute);
  margin: 2px 0 6px;
}
@media (max-width: 900px) {
  .two {
    grid-template-columns: 1fr;
  }
}
</style>
