<template>
  <div class="pipeline page" v-loading="booting">
    <div class="pipe-head panel" v-if="pipeline">
      <div>
        <div class="kicker">Pipeline</div>
        <h2>{{ pipeline.name }}</h2>
        <p>
          {{ t('pipeline.linkedProject') }}<strong>{{ pipeline.project_name || pid }}</strong>
          <span v-if="pipeline.description"> · {{ pipeline.description }}</span>
        </p>
      </div>
      <router-link class="back" to="/pipeline">{{ t('pipeline.backList') }}</router-link>
    </div>

    <div class="steps panel">
      <button
        v-for="(s, i) in steps"
        :key="s.key"
        class="step"
        :class="{ active: step === s.key, done: stepIndex > i }"
        @click="goStep(s.key)"
      >
        <span class="num">{{ i + 1 }}</span>
        <span class="label">
          <strong>{{ t(s.titleKey) }}</strong>
          <small>{{ t(s.descKey) }}</small>
        </span>
      </button>
    </div>

    <!-- Step 1: requirements -->
    <section v-show="step === 'req'" class="stage panel">
      <header class="stage-head">
        <div>
          <h3>{{ t('pipeline.req.title') }}</h3>
          <p>{{ t('pipeline.req.tip') }}</p>
        </div>
        <el-button type="primary" :disabled="!canNextFromReq" @click="goStep('cases')">
          {{ t('pipeline.req.next') }}
        </el-button>
      </header>

      <el-form label-position="top" class="req-form">
        <el-form-item :label="t('pipeline.req.titleLabel')">
          <el-input v-model="reqTitle" :placeholder="t('pipeline.req.titlePh')" />
        </el-form-item>
        <el-form-item :label="t('pipeline.req.bodyLabel')">
          <el-input
            v-model="reqContent"
            type="textarea"
            :rows="10"
            :placeholder="t('pipeline.req.bodyPh')"
          />
        </el-form-item>
        <div class="req-actions">
          <el-upload :auto-upload="false" :show-file-list="!!fileName" :on-change="onFile" :limit="1">
            <el-button>{{ t('pipeline.req.pickFile') }}</el-button>
          </el-upload>
          <el-button type="primary" :loading="uploading" @click="uploadRequirement">{{ t('pipeline.req.save') }}</el-button>
        </div>
      </el-form>

      <div class="doc-list" v-if="docs.length">
        <div class="block-title">{{ t('pipeline.req.docs') }}</div>
        <article v-for="d in docs" :key="d.id" class="doc">
          <div>
            <strong>{{ d.title }}</strong>
            <div class="meta">{{ d.status }} · {{ d.chunk_count }} chunks</div>
          </div>
          <el-button link type="danger" @click="removeDoc(d.id)">{{ t('common.delete') }}</el-button>
        </article>
      </div>
    </section>

    <!-- Step 2: generate cases -->
    <section v-show="step === 'cases'" class="stage panel">
      <header class="stage-head">
        <div>
          <h3>{{ t('pipeline.cases.title') }}</h3>
          <p>{{ t('pipeline.cases.tip') }}</p>
        </div>
        <div class="head-actions">
          <el-button @click="goStep('req')">{{ t('common.previous') }}</el-button>
          <el-button type="primary" :disabled="!confirmedCases.length" @click="goStep('report')">
            {{ t('pipeline.cases.next') }}
          </el-button>
        </div>
      </header>

      <div class="gen-toolbar">
        <el-select v-model="templateId" :placeholder="t('pipeline.cases.template')" style="width: 200px">
          <el-option v-for="tpl in templates" :key="tpl.id" :label="tpl.name" :value="tpl.id" />
        </el-select>
        <el-button :loading="startingPoints" @click="startPoints">{{ t('pipeline.cases.genPoints') }}</el-button>
        <el-button type="primary" plain :disabled="!confirmedPoints.length" :loading="startingCases" @click="startCases">
          {{ t('pipeline.cases.genCases') }}
        </el-button>
        <el-button link type="primary" :disabled="!draftPoints.length" @click="confirmAllPoints">{{ t('pipeline.cases.confirmAllPoints') }}</el-button>
        <el-button link type="primary" :disabled="!draftCases.length" @click="confirmAllCases">{{ t('pipeline.cases.confirmAllCases') }}</el-button>
      </div>

      <div class="gen-grid">
        <div class="chat-col">
          <ChatPanel
            v-if="activeSessionId"
            :key="activeSessionId"
            :session-id="activeSessionId"
            @artifact="refreshArtifacts"
            @done="refreshArtifacts"
          />
          <div v-else class="chat-empty">
            点击上方「生成测试点」或「生成用例」开始对话。首次可把需求要点再发一条给引擎。
          </div>
        </div>
        <aside class="artifact-col">
          <div class="block-title">{{ t('pipeline.cases.points') }} <small>{{ points.length }}</small></div>
          <article v-for="p in points" :key="p.id" class="art-item">
            <div class="art-top">
              <strong>{{ p.title }}</strong>
              <span class="status-pill" :class="p.status === 'CONFIRMED' ? '' : 'warn'">{{ p.status }}</span>
            </div>
            <el-button v-if="p.status !== 'CONFIRMED'" link type="primary" @click="confirmPoint(p)">{{ t('common.confirm') }}</el-button>
          </article>

          <div class="block-title" style="margin-top: 18px">{{ t('pipeline.cases.cases') }} <small>{{ cases.length }}</small></div>
          <article v-for="c in cases" :key="c.id" class="art-item">
            <div class="art-top">
              <strong>{{ c.title }}</strong>
              <span class="conf">{{ Number(c.confidence || 0).toFixed(2) }}</span>
            </div>
            <div class="art-meta">
              <span class="status-pill" :class="c.status === 'CONFIRMED' ? '' : 'warn'">{{ c.status }}</span>
            </div>
            <el-button v-if="c.status !== 'CONFIRMED'" link type="primary" @click="confirmCase(c)">{{ t('common.confirm') }}</el-button>
          </article>
        </aside>
      </div>
    </section>

    <!-- Step 3: report -->
    <section v-show="step === 'report'" class="stage panel">
      <header class="stage-head">
        <div>
          <h3>{{ t('pipeline.report.title') }}</h3>
          <p>{{ t('pipeline.report.tip') }}</p>
        </div>
        <div class="head-actions">
          <el-button @click="goStep('cases')">{{ t('common.previous') }}</el-button>
          <el-button type="primary" :disabled="!confirmedCases.length" :loading="startingRun" @click="startExecute">
            {{ t('pipeline.report.run') }}
          </el-button>
        </div>
      </header>

      <div class="gen-grid">
        <div class="chat-col">
          <ChatPanel
            v-if="runSessionId"
            :key="runSessionId"
            :session-id="runSessionId"
            @artifact="reloadReports"
            @done="reloadReports"
          />
          <div v-else class="chat-empty">
            {{ t('pipeline.report.emptyChat', { n: confirmedCases.length }) }}
          </div>
        </div>
        <aside class="artifact-col">
          <div class="block-title">{{ t('pipeline.report.runs') }}</div>
          <article v-for="r in runs" :key="r.id" class="art-item">
            <div class="art-top">
              <strong class="mono">{{ r.id.slice(0, 8) }}</strong>
              <span class="status-pill" :class="r.status === 'DONE' ? '' : 'warn'">{{ r.status }}</span>
            </div>
            <div class="art-meta">{{ t('pipeline.report.casesCount', { n: (r.case_ids_json || []).length }) }}</div>
          </article>

          <div class="block-title" style="margin-top: 18px">{{ t('pipeline.report.reports') }}</div>
          <article v-for="rep in reports" :key="rep.id" class="art-item report" @click="selectedReport = rep">
            <div class="art-top">
              <strong class="mono">{{ rep.id.slice(0, 8) }}</strong>
              <span class="status-pill">{{ rep.status }}</span>
            </div>
            <div class="summary">{{ formatSummary(rep.summary_json) }}</div>
          </article>
          <el-empty v-if="!reports.length" :description="t('pipeline.report.noReport')" :image-size="64" />
        </aside>
      </div>

      <div v-if="selectedReport" class="report-detail panel">
        <div class="block-title">{{ t('pipeline.report.detail') }}</div>
        <pre>{{ JSON.stringify(selectedReport, null, 2) }}</pre>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import ChatPanel from '../components/ChatPanel.vue'

type StepKey = 'req' | 'cases' | 'report'

const { t } = useI18n()
const route = useRoute()
const pipelineId = computed(() => String(route.params.pipelineId || ''))
const pipeline = ref<any>(null)
const pid = ref('')

const steps = [
  { key: 'req' as const, titleKey: 'pipeline.steps.reqTitle', descKey: 'pipeline.steps.reqDesc' },
  { key: 'cases' as const, titleKey: 'pipeline.steps.casesTitle', descKey: 'pipeline.steps.casesDesc' },
  { key: 'report' as const, titleKey: 'pipeline.steps.reportTitle', descKey: 'pipeline.steps.reportDesc' },
]

const step = ref<StepKey>('req')
const stepIndex = computed(() => steps.findIndex((s) => s.key === step.value))

const booting = ref(true)
const uploading = ref(false)
const reqTitle = ref('')
const reqContent = ref('')
const fileName = ref('')
const file = ref<File | null>(null)
const docs = ref<any[]>([])

const templates = ref<any[]>([])
const templateId = ref('')
const points = ref<any[]>([])
const cases = ref<any[]>([])
const activeSessionId = ref('')
const startingPoints = ref(false)
const startingCases = ref(false)

const runSessionId = ref('')
const startingRun = ref(false)
const runs = ref<any[]>([])
const reports = ref<any[]>([])
const selectedReport = ref<any>(null)

const draftPoints = computed(() => points.value.filter((p) => p.status !== 'CONFIRMED'))
const confirmedPoints = computed(() => points.value.filter((p) => p.status === 'CONFIRMED'))
const draftCases = computed(() => cases.value.filter((c) => c.status !== 'CONFIRMED'))
const confirmedCases = computed(() => cases.value.filter((c) => c.status === 'CONFIRMED'))
const canNextFromReq = computed(() => docs.value.length > 0 || !!reqContent.value.trim())

async function goStep(key: StepKey) {
  step.value = key
  if (pipelineId.value) {
    try {
      await api.patchPipeline(pipelineId.value, { step: key })
      if (pipeline.value) pipeline.value.step = key
    } catch {
      /* ignore */
    }
  }
  if (key === 'cases') refreshArtifacts()
  if (key === 'report') reloadReports()
}

function onFile(f: any) {
  file.value = f.raw
  fileName.value = f.name
  if (!reqTitle.value) reqTitle.value = f.name
}

async function uploadRequirement() {
  if (!reqContent.value.trim() && !file.value) {
    ElMessage.warning(t('pipeline.req.warnEmpty'))
    return
  }
  uploading.value = true
  try {
    const form = new FormData()
    form.append('title', reqTitle.value || 'req')
    if (file.value) form.append('file', file.value)
    else form.append('content', reqContent.value)
    await api.uploadRag(pid.value, form)
    localStorage.setItem(`pipeline_req_${pid.value}`, reqContent.value || reqTitle.value)
    ElMessage.success(t('pipeline.req.saved'))
    reqContent.value = ''
    file.value = null
    fileName.value = ''
    await loadDocs()
  } finally {
    uploading.value = false
  }
}

async function removeDoc(id: string) {
  await api.deleteRag(pid.value, id)
  await loadDocs()
}

async function loadDocs() {
  docs.value = await api.listRagDocs(pid.value)
}

async function refreshArtifacts() {
  points.value = await api.listTestPoints(pid.value)
  cases.value = await api.listTestCases(pid.value)
}

async function startPoints() {
  startingPoints.value = true
  try {
    const s = await api.createSession({
      project_id: pid.value,
      flow_type: 'TEST_POINT',
      title: '流水线-测试点',
    })
    activeSessionId.value = s.id
    ElMessage.success(t('pipeline.cases.sessionPoints'))
  } finally {
    startingPoints.value = false
  }
}

async function startCases() {
  startingCases.value = true
  try {
    const s = await api.createSession({
      project_id: pid.value,
      flow_type: 'TEST_CASE',
      title: '流水线-用例',
      template_id: templateId.value || null,
    })
    activeSessionId.value = s.id
    ElMessage.success(t('pipeline.cases.sessionCases'))
  } finally {
    startingCases.value = false
  }
}

async function confirmPoint(row: any) {
  await api.patchTestPoint(row.id, { status: 'CONFIRMED' })
  await refreshArtifacts()
}

async function confirmCase(row: any) {
  await api.patchTestCase(row.id, { status: 'CONFIRMED' })
  await refreshArtifacts()
}

async function confirmAllPoints() {
  await Promise.all(draftPoints.value.map((p) => api.patchTestPoint(p.id, { status: 'CONFIRMED' })))
  ElMessage.success(t('pipeline.cases.allPointsOk'))
  await refreshArtifacts()
}

async function confirmAllCases() {
  await Promise.all(draftCases.value.map((c) => api.patchTestCase(c.id, { status: 'CONFIRMED' })))
  ElMessage.success(t('pipeline.cases.allCasesOk'))
  await refreshArtifacts()
}

async function startExecute() {
  startingRun.value = true
  try {
    const s = await api.createSession({
      project_id: pid.value,
      flow_type: 'TEST_EXECUTE',
      title: '流水线-执行',
    })
    runSessionId.value = s.id
    ElMessage.success(t('pipeline.report.sessionOk'))
  } finally {
    startingRun.value = false
  }
}

async function reloadReports() {
  runs.value = await api.listRuns(pid.value)
  const all = await api.listReports()
  const runIds = new Set(runs.value.map((r) => r.id))
  reports.value = all.filter((r: any) => runIds.has(r.run_id))
}

function formatSummary(s: any) {
  if (!s) return '—'
  if (typeof s === 'string') return s
  const total = s.total ?? '-'
  const passed = s.passed ?? '-'
  const failed = s.failed ?? '-'
  return `total ${total} · pass ${passed} · fail ${failed}`
}

watch(pipelineId, async () => {
  await boot()
})

async function boot() {
  booting.value = true
  try {
    if (!pipelineId.value) {
      ElMessage.error(t('pipeline.missingId'))
      return
    }
    pipeline.value = await api.getPipeline(pipelineId.value)
    pid.value = pipeline.value.project_id
    const saved = pipeline.value.step as StepKey
    if (saved && ['req', 'cases', 'report'].includes(saved)) step.value = saved
    templates.value = await api.listTemplates(pid.value)
    if (templates.value[0]) templateId.value = templates.value[0].id
    await loadDocs()
    await refreshArtifacts()
    await reloadReports()
  } finally {
    booting.value = false
  }
}

onMounted(boot)
</script>

<style scoped>
.pipeline {
  display: grid;
  gap: 14px;
}

.pipe-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 18px 20px;
}

.pipe-head .kicker {
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--teal-deep);
  font-weight: 650;
}

.pipe-head h2 {
  margin: 4px 0 0;
  font-family: var(--font-brand);
  font-size: 24px;
}

.pipe-head p {
  margin: 8px 0 0;
  color: var(--mute);
  font-size: 13px;
}

.pipe-head .back {
  color: var(--teal-deep);
  text-decoration: none;
  font-weight: 650;
  font-size: 13px;
  white-space: nowrap;
}

.steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 10px;
}

.step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  cursor: pointer;
  text-align: left;
  font: inherit;
  color: inherit;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.step:hover {
  background: rgba(15, 143, 134, 0.06);
}

.step.active {
  background: linear-gradient(135deg, rgba(15, 143, 134, 0.16), rgba(15, 143, 134, 0.06));
  border-color: rgba(15, 143, 134, 0.28);
}

.step.done .num {
  background: var(--teal);
  color: #fff;
}

.num {
  width: 28px;
  height: 28px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: rgba(18, 32, 43, 0.08);
  font-family: var(--font-brand);
  font-weight: 700;
  font-size: 13px;
  flex-shrink: 0;
}

.step.active .num {
  background: var(--teal);
  color: #fff;
}

.label {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.label strong {
  font-family: var(--font-brand);
  font-size: 14px;
}

.label small {
  color: var(--mute);
  font-size: 12px;
}

.stage {
  padding: 18px;
}

.stage-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.stage-head h3 {
  margin: 0;
  font-family: var(--font-brand);
  font-size: 20px;
}

.stage-head p {
  margin: 6px 0 0;
  color: var(--mute);
  font-size: 13px;
}

.head-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.req-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.doc-list {
  margin-top: 18px;
  border-top: 1px solid var(--line);
  padding-top: 14px;
}

.block-title {
  font-family: var(--font-brand);
  font-weight: 650;
  margin-bottom: 10px;
  display: flex;
  gap: 8px;
  align-items: baseline;
}

.block-title small {
  color: var(--mute);
  font-family: var(--font-mono);
}

.doc {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
}

.doc .meta {
  color: var(--mute);
  font-size: 12px;
  margin-top: 4px;
}

.gen-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.gen-grid {
  display: grid;
  grid-template-columns: 1.4fr 0.9fr;
  gap: 14px;
}

.chat-empty {
  min-height: 420px;
  border: 1px dashed var(--line-strong);
  border-radius: 14px;
  display: grid;
  place-items: center;
  padding: 24px;
  color: var(--mute);
  text-align: center;
  background: rgba(255, 255, 255, 0.45);
}

.artifact-col {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.55);
  max-height: 680px;
  overflow: auto;
}

.art-item {
  padding: 10px 0;
  border-top: 1px solid var(--line);
}

.art-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: flex-start;
}

.art-meta {
  margin: 6px 0;
}

.conf {
  font-family: var(--font-mono);
  color: var(--teal-deep);
  font-weight: 700;
}

.mono {
  font-family: var(--font-mono);
}

.summary {
  margin-top: 6px;
  font-size: 12px;
  color: var(--ink-soft);
}

.report {
  cursor: pointer;
}

.report:hover {
  background: rgba(15, 143, 134, 0.05);
}

.report-detail {
  margin-top: 14px;
  padding: 14px;
}

.report-detail pre {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  white-space: pre-wrap;
  color: var(--ink-soft);
  max-height: 320px;
  overflow: auto;
}

@media (max-width: 1000px) {
  .steps {
    grid-template-columns: 1fr;
  }
  .gen-grid {
    grid-template-columns: 1fr;
  }
  .stage-head {
    flex-direction: column;
  }
}
</style>
