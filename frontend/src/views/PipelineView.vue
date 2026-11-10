<template>
  <div class="pipeline page" v-loading="booting">
    <div class="pipe-head panel" v-if="pipeline">
      <div>
        <div class="kicker">{{ t(pipelineKindOf(pipeline.kind).titleKey) }}</div>
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

      <OpenApiImportPanel
        v-if="pid"
        class="openapi-block"
        :project-id="pid"
        :pipeline-id="pipelineId"
        @imported="onOpenApiImported"
      />

      <div class="doc-list" v-if="docs.length">
        <div class="block-title">{{ t('pipeline.req.docs') }}</div>
        <article v-for="d in docs" :key="d.id" class="doc">
          <div>
            <strong>{{ d.title }}</strong>
            <div class="meta">
              {{ d.status }} · {{ d.chunk_count }} chunks
              <span v-if="d.pipeline_id === pipelineId"> · {{ t('pipeline.req.scoped') }}</span>
            </div>
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
        <el-button @click="templateDrawer = true">{{ t('pipeline.cases.manageTemplates') }}</el-button>
        <el-button :loading="startingPoints" @click="startPoints">{{ t('pipeline.cases.genPoints') }}</el-button>
        <el-button type="primary" plain :disabled="!confirmedPoints.length" :loading="startingCases" @click="startCases">
          {{ t('pipeline.cases.genCases') }}
        </el-button>
        <el-button link type="primary" :disabled="!draftPoints.length" @click="confirmAllPoints">{{ t('pipeline.cases.confirmAllPoints') }}</el-button>
        <el-button link type="primary" :disabled="!draftCases.length" @click="confirmAllCases">{{ t('pipeline.cases.confirmAllCases') }}</el-button>
        <el-button :disabled="!cases.length" @click="exportCases('json')">{{ t('pipeline.cases.exportJson') }}</el-button>
        <el-button :disabled="!cases.length" @click="exportCases('postman')">{{ t('pipeline.cases.exportPostman') }}</el-button>
      </div>

      <el-drawer v-model="templateDrawer" :title="t('templates.title')" size="520px">
        <TemplatesView v-if="pid" :project-id="pid" @changed="loadTemplates" />
      </el-drawer>

      <CoverageBoard v-if="pid" ref="coverageRef" class="coverage-block" :project-id="pid" :pipeline-id="pipelineId" />

      <VersionRegressionPanel
        v-if="pid && pipeline?.kind === 'version_regression'"
        class="vreg-block"
        :project-id="pid"
        :pipeline-id="pipelineId"
        @generated="onRegressionGenerated"
        @ran="reloadReports"
      />

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

          <div class="block-title" style="margin-top: 18px">
            {{ t('pipeline.cases.cases') }}
            <small>{{ cases.length }}</small>
            <ConfidenceBadge v-if="cases.length" :value="avgCaseConfidence" />
          </div>
          <article v-for="c in cases" :key="c.id" class="art-item">
            <div class="art-top">
              <strong>{{ c.title }}</strong>
              <ConfidenceBadge :value="c.confidence" />
            </div>
            <div class="art-meta">
              <span class="status-pill" :class="c.status === 'CONFIRMED' ? '' : 'warn'">{{ c.status }}</span>
              <span
                v-if="c.content_json?._skill_compliance"
                class="skill-pill"
                :class="(c.content_json._skill_compliance.missed || []).length ? 'warn' : 'ok'"
              >
                {{ skillLabel(c.content_json._skill_compliance) }}
              </span>
            </div>
            <div class="art-actions">
              <el-button link type="primary" @click="openCaseEditor(c)">{{ t('common.edit') }}</el-button>
              <el-button v-if="c.status !== 'CONFIRMED'" link type="primary" @click="confirmCase(c)">{{ t('common.confirm') }}</el-button>
              <el-button link type="primary" :loading="runningCaseId === c.id" @click="startSingleCase(c)">
                {{ t('pipeline.cases.runOne') }}
              </el-button>
              <el-button link type="danger" @click="removeCase(c)">{{ t('common.delete') }}</el-button>
            </div>
          </article>
        </aside>
      </div>

      <CaseEditor v-model="caseEditorOpen" :case-row="editingCase" @saved="refreshArtifacts" />
    </section>

    <!-- Step 3: report -->
    <section v-show="step === 'report'" class="stage panel">
      <header class="stage-head">
        <div>
          <h3>{{ t('pipeline.report.title') }}</h3>
          <p>{{ t('pipeline.report.tip') }}</p>
        </div>
        <div class="head-actions">
          <el-select v-model="runEnvId" :placeholder="t('pipeline.report.env')" style="width: 220px">
            <el-option
              v-for="e in execEnvs"
              :key="e.id"
              :label="`${e.name} · ${e.base_url || t('pipeline.report.noBase')}`"
              :value="e.id"
            />
          </el-select>
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
            :test-case-ids="runCaseIds"
            :initial-message="runKickoff"
            :env-id="runEnvId"
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
            <div v-if="rep.summary_json?.confidence_avg != null" class="summary-conf">
              <ConfidenceBadge :value="rep.summary_json.confidence_avg" />
            </div>
          </article>
          <el-empty v-if="!reports.length" :description="t('pipeline.report.noReport')" :image-size="64" />
        </aside>
      </div>

      <div v-if="selectedReport" class="report-detail panel">
        <div class="block-title">{{ t('pipeline.report.detail') }}</div>
        <ReportViewer :report="selectedReport" />
      </div>

      <div class="ops-grid">
        <div class="panel">
          <SchedulePanel v-if="pid" :project-id="pid" :pipeline-id="pipelineId" @ran="reloadReports" />
        </div>
        <div class="panel">
          <DefectConfigPanel v-if="pid" :project-id="pid" :pipeline-id="pipelineId" />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import ChatPanel from '../components/ChatPanel.vue'
import ConfidenceBadge from '../components/ConfidenceBadge.vue'
import CaseEditor from '../components/CaseEditor.vue'
import ReportViewer from '../components/ReportViewer.vue'
import TemplatesView from './TemplatesView.vue'
import OpenApiImportPanel from '../components/OpenApiImportPanel.vue'
import CoverageBoard from '../components/CoverageBoard.vue'
import VersionRegressionPanel from '../components/VersionRegressionPanel.vue'
import { pipelineKindOf } from '../pipelineKinds'
import SchedulePanel from '../components/SchedulePanel.vue'
import DefectConfigPanel from '../components/DefectConfigPanel.vue'
import { usePetStore } from '../stores/pet'

type StepKey = 'req' | 'cases' | 'report'

const { t } = useI18n()
const route = useRoute()
const pet = usePetStore()
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
const templateDrawer = ref(false)
const points = ref<any[]>([])
const cases = ref<any[]>([])
const activeSessionId = ref('')
const startingPoints = ref(false)
const startingCases = ref(false)

const runSessionId = ref('')
const runCaseIds = ref<string[]>([])
const runKickoff = ref('')
const startingRun = ref(false)
const execProject = ref<any>(null)
const runEnvId = ref('')
const execEnvs = computed(() => {
  const p = execProject.value
  if (!p) return []
  const listed = Array.isArray(p.runtime_envs) ? p.runtime_envs.filter((e: any) => e && (e.id || e.name)) : []
  if (listed.length) {
    return listed.map((e: any) => ({ ...e, id: e.id || e.name }))
  }
  return [{ id: 'default', name: 'default', base_url: p.runtime_base_url || '', is_default: true }]
})
const runningCaseId = ref('')
const runs = ref<any[]>([])
const reports = ref<any[]>([])
const selectedReport = ref<any>(null)
const caseEditorOpen = ref(false)
const editingCase = ref<any>(null)
const coverageRef = ref<{ load: () => Promise<void> } | null>(null)
const specsCount = ref(0)

const draftPoints = computed(() => points.value.filter((p) => p.status !== 'CONFIRMED'))
const confirmedPoints = computed(() => points.value.filter((p) => p.status === 'CONFIRMED'))
const draftCases = computed(() => cases.value.filter((c) => c.status !== 'CONFIRMED'))
const confirmedCases = computed(() => cases.value.filter((c) => c.status === 'CONFIRMED'))
const avgCaseConfidence = computed(() => {
  if (!cases.value.length) return 0
  const sum = cases.value.reduce((acc, c) => acc + Number(c.confidence || 0), 0)
  return sum / cases.value.length
})
const canNextFromReq = computed(() => docs.value.length > 0 || specsCount.value > 0 || !!reqContent.value.trim())

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
  if (key === 'cases') {
    refreshArtifacts()
    coverageRef.value?.load()
  }
  if (key === 'report') reloadReports()
}

async function onRegressionGenerated() {
  await refreshArtifacts()
  coverageRef.value?.load()
}

async function onOpenApiImported() {
  try {
    const specs = await api.listApiSpecs(pid.value, pipelineId.value)
    specsCount.value = specs.length
  } catch {
    specsCount.value += 1
  }
  await refreshArtifacts()
  coverageRef.value?.load()
  goStep('cases')
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
    form.append('pipeline_id', pipelineId.value)
    if (file.value) form.append('file', file.value)
    else form.append('content', reqContent.value)
    await api.uploadRag(pid.value, form)
    localStorage.setItem(`pipeline_req_${pid.value}`, reqContent.value || reqTitle.value)
    ElMessage.success(t('pipeline.req.saved'))
    pet.completeQuest('upload_req')
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
  // Prefer docs bound to this pipeline so requirements don't leak across pipelines.
  const scoped = await api.listRagDocs(pid.value, undefined, pipelineId.value)
  docs.value = scoped.length ? scoped : await api.listRagDocs(pid.value)
}

async function refreshArtifacts() {
  points.value = await api.listTestPoints(pid.value, pipelineId.value)
  cases.value = await api.listTestCases(pid.value, pipelineId.value)
}

async function startPoints() {
  startingPoints.value = true
  try {
    const s = await api.createSession({
      project_id: pid.value,
      pipeline_id: pipelineId.value,
      flow_type: 'TEST_POINT',
      title: '流水线-测试点',
    })
    activeSessionId.value = s.id
    pet.completeQuest('gen_cases')
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
      pipeline_id: pipelineId.value,
      flow_type: 'TEST_CASE',
      title: '流水线-用例',
      template_id: templateId.value || null,
    })
    activeSessionId.value = s.id
    pet.completeQuest('gen_cases')
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

function openCaseEditor(row: any) {
  editingCase.value = row
  caseEditorOpen.value = true
}

async function removeCase(row: any) {
  try {
    await ElMessageBox.confirm(t('pipeline.cases.confirmDelete', { title: row.title }), {
      type: 'warning',
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
    })
  } catch {
    return
  }
  await api.deleteTestCase(row.id)
  ElMessage.success(t('pipeline.cases.deleted'))
  await refreshArtifacts()
}

function downloadJson(filename: string, data: any) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function exportCases(format: 'json' | 'postman') {
  const data = await api.exportCases(pid.value, pipelineId.value, format)
  const name =
    format === 'postman'
      ? `${pipeline.value?.name || 'ai-test'}.postman_collection.json`
      : `${pipeline.value?.name || 'ai-test'}-cases.json`
  downloadJson(name, data)
  ElMessage.success(t('pipeline.cases.exported'))
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
  const env = execEnvs.value.find((e) => e.id === runEnvId.value) || execEnvs.value[0]
  if (!env?.base_url) {
    ElMessage.warning(t('pipeline.report.needEnv'))
    return
  }
  startingRun.value = true
  try {
    await openExecuteSession(confirmedCases.value.map((c) => c.id), t('pipeline.report.kickoff'))
    ElMessage.success(t('pipeline.report.sessionOk'))
  } finally {
    startingRun.value = false
  }
}

async function startSingleCase(row: any) {
  const env = execEnvs.value.find((e) => e.id === runEnvId.value) || execEnvs.value[0]
  if (!env?.base_url) {
    ElMessage.warning(t('pipeline.report.needEnv'))
    return
  }
  runningCaseId.value = row.id
  try {
    if (row.status !== 'CONFIRMED') {
      await api.patchTestCase(row.id, { status: 'CONFIRMED' })
      await refreshArtifacts()
    }
    step.value = 'report'
    await api.patchPipeline(pipelineId.value, { step: 'report' })
    await openExecuteSession([row.id], t('pipeline.cases.kickoffOne', { title: row.title }))
    ElMessage.success(t('pipeline.cases.sessionOne'))
  } finally {
    runningCaseId.value = ''
  }
}

async function openExecuteSession(caseIds: string[], kickoff: string) {
  const s = await api.createSession({
    project_id: pid.value,
    pipeline_id: pipelineId.value,
    flow_type: 'TEST_EXECUTE',
    title: caseIds.length === 1 ? '流水线-单次执行' : '流水线-执行',
  })
  runCaseIds.value = caseIds
  runKickoff.value = kickoff
  runSessionId.value = s.id
}

async function reloadReports() {
  runs.value = await api.listRuns(pid.value, pipelineId.value)
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
  const time = s.time_ms != null ? ` · ${s.time_ms}ms` : ''
  const conf = s.confidence_avg != null ? ` · conf ${Math.round(Number(s.confidence_avg) * 100)}%` : ''
  const mcp = s.mcp_calls != null ? ` · mcp ${s.mcp_calls}` : ''
  const env = s.env_name ? ` · ${s.env_name}` : ''
  return `total ${total} · pass ${passed} · fail ${failed}${time}${conf}${mcp}${env}`
}

function skillLabel(comp: any) {
  if (!comp) return ''
  const missed = comp.missed || []
  if (missed.length) return t('pipeline.cases.skillMiss', { n: missed.length })
  return t('pipeline.cases.skillOk')
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
    try {
      execProject.value = await api.getProject(pid.value)
      const envs = execEnvs.value
      const def = envs.find((e) => e.is_default) || envs[0]
      if (def && !runEnvId.value) runEnvId.value = def.id
    } catch {
      execProject.value = null
    }
    const saved = pipeline.value.step as StepKey
    if (saved && ['req', 'cases', 'report'].includes(saved)) step.value = saved
    await loadTemplates()
    await loadDocs()
    try {
      const specs = await api.listApiSpecs(pid.value, pipelineId.value)
      specsCount.value = specs.length
    } catch {
      specsCount.value = 0
    }
    await refreshArtifacts()
    await reloadReports()
  } finally {
    booting.value = false
  }
}

async function loadTemplates() {
  templates.value = await api.listTemplates(pid.value)
  if (!templateId.value && templates.value[0]) templateId.value = templates.value[0].id
  if (templateId.value && !templates.value.some((t) => t.id === templateId.value) && templates.value[0]) {
    templateId.value = templates.value[0].id
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
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.skill-pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 650;
}
.skill-pill.ok {
  background: rgba(47, 157, 106, 0.12);
  color: var(--ok);
}
.skill-pill.warn {
  background: rgba(201, 133, 45, 0.14);
  color: var(--amber);
}

.art-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.summary-conf {
  margin-top: 6px;
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

.openapi-block,
.coverage-block,
.vreg-block {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.ops-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 14px;
}

@media (max-width: 1000px) {
  .steps {
    grid-template-columns: 1fr;
  }
  .gen-grid,
  .ops-grid {
    grid-template-columns: 1fr;
  }
  .stage-head {
    flex-direction: column;
  }
}
</style>
