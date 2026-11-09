<template>
  <div class="page dash" v-loading="loading">
    <div class="page-head">
      <div>
        <h2>{{ t('dash.title') }}</h2>
        <p>{{ t('dash.subtitle') }}</p>
      </div>
      <el-button @click="load">{{ t('dash.refresh') }}</el-button>
    </div>

    <section class="kpis">
      <article class="kpi panel">
        <div class="k">{{ t('dash.kpiPipelines') }}</div>
        <div class="v">{{ data.pipeline_count || 0 }}</div>
      </article>
      <article class="kpi panel">
        <div class="k">{{ t('dash.kpiGenAvg') }}</div>
        <div class="v">{{ pct(data.overall_generation?.avg) }}%</div>
        <div class="sub">{{ t('dash.genHint') }}</div>
      </article>
      <article class="kpi panel">
        <div class="k">{{ t('dash.kpiRunAvg') }}</div>
        <div class="v">{{ pct(data.overall_run?.avg) }}%</div>
        <div class="sub">{{ t('dash.runHint') }}</div>
      </article>
    </section>

    <section class="list-block">
      <div class="list-head">
        <h3>{{ t('dash.reqTitle') }}</h3>
        <span class="count">{{ (data.pipelines || []).length }}</span>
      </div>
      <div v-if="!(data.pipelines || []).length" class="empty-hint">{{ t('dash.empty') }}</div>
      <button
        v-for="row in data.pipelines || []"
        :key="row.pipeline_id"
        class="card panel"
        :class="{ open: selectedId === row.pipeline_id }"
        @click="open(row.pipeline_id)"
      >
        <div class="card-top">
          <div>
            <h3>{{ row.name }}</h3>
            <p>{{ t('dash.project') }}{{ row.project_name || row.project_id }}</p>
          </div>
          <ConfidenceBadge :value="row.generation?.avg" />
        </div>
        <div class="bars">
          <div class="bar-row">
            <span>{{ t('dash.genAvg') }}</span>
            <div class="track"><i :style="{ width: pct(row.generation?.avg) + '%' }" /></div>
            <b>{{ pct(row.generation?.avg) }}%</b>
          </div>
          <div class="bar-row">
            <span>{{ t('dash.runAvg') }}</span>
            <div class="track"><i class="run" :style="{ width: pct(row.latest_run?.overall_confidence) + '%' }" /></div>
            <b>{{ pct(row.latest_run?.overall_confidence) }}%</b>
          </div>
        </div>
        <div class="meta">
          <span>{{ t('dash.casesN', { n: row.generation?.count || 0 }) }}</span>
          <span>{{ t('dash.runsN', { n: row.run_count || 0 }) }}</span>
          <span v-if="row.latest_run">{{ t('dash.lastScope', { s: scopeLabel(row.latest_run.scope) }) }}</span>
        </div>
      </button>
    </section>

    <section v-if="detail" class="detail panel">
      <header class="detail-head">
        <div>
          <div class="kicker">{{ t('dash.reqDetail') }}</div>
          <h3>{{ detail.name }}</h3>
        </div>
        <el-button link type="primary" @click="$router.push(`/pipelines/${detail.pipeline_id}`)">
          {{ t('dash.openPipeline') }}
        </el-button>
      </header>

      <div class="split">
        <div>
          <div class="block-title">{{ t('dash.caseList') }}</div>
          <article v-for="c in detail.cases || []" :key="c.id" class="row">
            <strong>{{ c.title }}</strong>
            <ConfidenceBadge :value="c.confidence" />
          </article>
          <el-empty v-if="!(detail.cases || []).length" :description="t('dash.noCases')" :image-size="56" />
        </div>
        <div>
          <div class="block-title">{{ t('dash.runList') }}</div>
          <article v-for="r in detail.runs || []" :key="r.run_id" class="row">
            <div>
              <strong class="mono">{{ String(r.run_id).slice(0, 8) }}</strong>
              <div class="muted">{{ scopeLabel(r.scope) }} · {{ r.status }} · {{ t('dash.passFail', { p: r.passed ?? '—', f: r.failed ?? '—' }) }}</div>
            </div>
            <ConfidenceBadge :value="r.overall_confidence" />
          </article>
          <el-empty v-if="!(detail.runs || []).length" :description="t('dash.noRuns')" :image-size="56" />
        </div>
      </div>

      <div class="events" v-if="(detail.events || []).length">
        <div class="block-title">{{ t('dash.eventList') }}</div>
        <article v-for="ev in detail.events" :key="ev.id" class="row">
          <div>
            <strong>{{ eventLabel(ev.event) }}</strong>
            <div class="muted">{{ ev.props?.title || ev.props?.case_title || ev.props?.scope || ev.event }}</div>
          </div>
          <ConfidenceBadge v-if="ev.confidence != null" :value="ev.confidence" />
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { useCurrentProject } from '../composables/useCurrentProject'
import ConfidenceBadge from '../components/ConfidenceBadge.vue'

const { t } = useI18n()
const { currentProjectId } = useCurrentProject()
const loading = ref(false)
const data = ref<any>({ pipelines: [] })
const detail = ref<any>(null)
const selectedId = ref('')

function pct(n: any) {
  const v = Number(n || 0)
  if (Number.isNaN(v)) return 0
  return Math.round(Math.max(0, Math.min(1, v)) * 100)
}

function scopeLabel(s: string) {
  return s === 'single' ? t('dash.scopeSingle') : t('dash.scopeSuite')
}

function eventLabel(name: string) {
  const key = `dash.event.${name}`
  const label = t(key)
  return label === key ? name : label
}

async function load() {
  loading.value = true
  try {
    data.value = await api.getDashboard(currentProjectId.value ? { project_id: currentProjectId.value } : {})
  } finally {
    loading.value = false
  }
}

async function open(id: string) {
  selectedId.value = id
  detail.value = await api.getDashboard({ pipeline_id: id })
}

watch(currentProjectId, () => {
  selectedId.value = ''
  detail.value = null
  void load()
})

onMounted(load)
</script>

<style scoped>
.kpis {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 18px;
}
.kpi {
  padding: 16px 18px;
}
.kpi .k {
  font-size: 12px;
  color: var(--mute);
}
.kpi .v {
  font-family: var(--font-brand);
  font-size: 32px;
  margin-top: 6px;
}
.kpi .sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--mute);
}
.list-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 10px;
}
.list-head h3 {
  margin: 0;
  font-family: var(--font-brand);
}
.count {
  font-family: var(--font-mono);
  color: var(--mute);
}
.card {
  display: block;
  width: 100%;
  text-align: left;
  font: inherit;
  color: inherit;
  cursor: pointer;
  padding: 16px 18px;
  margin-bottom: 10px;
  border: 1px solid var(--line);
}
.card.open {
  border-color: rgba(15, 143, 134, 0.4);
  box-shadow: 0 0 0 3px rgba(15, 143, 134, 0.08);
}
.card-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.card h3 {
  margin: 0;
  font-family: var(--font-brand);
  font-size: 18px;
}
.card p {
  margin: 4px 0 0;
  color: var(--mute);
  font-size: 13px;
}
.bars {
  margin-top: 12px;
  display: grid;
  gap: 8px;
}
.bar-row {
  display: grid;
  grid-template-columns: 88px 1fr 48px;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: var(--ink-soft);
}
.track {
  height: 8px;
  border-radius: 99px;
  background: rgba(18, 32, 43, 0.08);
  overflow: hidden;
}
.track i {
  display: block;
  height: 100%;
  background: var(--teal);
}
.track i.run {
  background: #2d628c;
}
.meta {
  display: flex;
  gap: 14px;
  margin-top: 10px;
  font-size: 12px;
  color: var(--mute);
}
.detail {
  margin-top: 18px;
  padding: 18px;
}
.detail-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
}
.kicker {
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--teal-deep);
  font-weight: 650;
}
.detail-head h3 {
  margin: 4px 0 0;
  font-family: var(--font-brand);
}
.split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.block-title {
  font-family: var(--font-brand);
  font-weight: 650;
  margin-bottom: 8px;
}
.row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 0;
  border-top: 1px solid var(--line);
  align-items: center;
}
.muted {
  color: var(--mute);
  font-size: 12px;
  margin-top: 4px;
}
.mono {
  font-family: var(--font-mono);
}
.events {
  margin-top: 18px;
  border-top: 1px solid var(--line);
  padding-top: 12px;
}
.empty-hint {
  color: var(--mute);
  padding: 24px 0;
}
@media (max-width: 900px) {
  .kpis,
  .split {
    grid-template-columns: 1fr;
  }
}
</style>
