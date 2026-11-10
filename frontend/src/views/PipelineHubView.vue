<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>{{ t('pipelineHub.title') }}</h2>
        <p>{{ t('pipelineHub.subtitle') }}</p>
      </div>
    </div>

    <section class="create panel">
      <div class="create-head">
        <div>
          <div class="kicker">New Pipeline</div>
          <h3>{{ t('pipelineHub.createTitle') }}</h3>
        </div>
        <p class="hint">{{ t('pipelineHub.createHint') }}</p>
      </div>
      <el-form label-position="top" @submit.prevent>
        <el-form-item :label="t('pipelineHub.kind')" required>
          <div class="kind-grid">
            <button
              v-for="k in kinds"
              :key="k.id"
              type="button"
              class="kind-card"
              :class="{ active: form.kind === k.id, disabled: !k.available }"
              :disabled="!k.available"
              @click="selectKind(k)"
            >
              <span class="kind-ico">{{ k.ico }}</span>
              <strong>{{ t(k.titleKey) }}</strong>
              <small>{{ t(k.descKey) }}</small>
              <span v-if="!k.available" class="soon">{{ t('pipelineHub.comingSoon') }}</span>
            </button>
          </div>
        </el-form-item>
        <div class="fields">
          <el-form-item :label="t('pipelineHub.name')" required>
            <el-input v-model="form.name" :placeholder="t('pipelineHub.namePh')" />
          </el-form-item>
          <el-form-item :label="t('pipelineHub.project')" required>
            <div class="project-row">
              <el-select v-model="form.project_id" filterable :placeholder="t('pipelineHub.projectPh')" style="flex: 1">
                <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
              <el-button @click="showNewProject = !showNewProject">
                {{ showNewProject ? t('pipelineHub.collapse') : t('pipelineHub.newProject') }}
              </el-button>
            </div>
          </el-form-item>
          <el-form-item :label="t('pipelineHub.desc')" class="span-2">
            <el-input v-model="form.description" type="textarea" :rows="2" :placeholder="t('pipelineHub.descPh')" />
          </el-form-item>
        </div>

        <div v-if="showNewProject" class="inline-project panel-soft">
          <div class="inline-title">{{ t('pipelineHub.quickTitle') }}</div>
          <div class="fields">
            <el-form-item :label="t('pipelineHub.projectName')" required>
              <el-input v-model="projectForm.name" :placeholder="t('pipelineHub.projectNamePh')" />
            </el-form-item>
            <el-form-item :label="t('pipelineHub.baseUrl')">
              <el-input v-model="projectForm.runtime_base_url" />
            </el-form-item>
          </div>
          <el-button type="primary" plain :loading="creatingProject" @click="createProjectQuick">
            {{ t('pipelineHub.createProjectSelect') }}
          </el-button>
        </div>

        <div class="actions">
          <el-button
            type="primary"
            size="large"
            :loading="creating"
            :disabled="!form.name.trim() || !form.project_id"
            @click="create"
          >
            {{ t('pipelineHub.createEnter') }}
          </el-button>
        </div>
      </el-form>
    </section>

    <section class="list-block">
      <div class="list-head">
        <h3>{{ t('pipelineHub.listTitle') }}</h3>
        <span class="count">{{ list.length }}</span>
      </div>

      <div v-loading="loading" class="grid">
        <button
          v-for="row in list"
          :key="row.id"
          class="tile"
          @click="$router.push(`/pipelines/${row.id}`)"
        >
          <div class="top">
            <span class="status-pill">{{ kindLabel(row.kind) }}</span>
            <span class="status-pill soft">{{ stepLabel(row.step) }}</span>
            <span class="mono">{{ String(row.id).slice(0, 8) }}</span>
          </div>
          <h3>{{ row.name }}</h3>
          <p>{{ row.description || '—' }}</p>
          <div class="foot">
            <span>{{ t('pipelineHub.projectLabel') }}{{ row.project_name || row.project_id.slice(0, 8) }}</span>
            <span class="go">{{ t('pipelineHub.enter') }}</span>
          </div>
        </button>
      </div>

      <div v-if="!loading && !list.length" class="empty-hint">{{ t('pipelineHub.empty') }}</div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { PIPELINE_KINDS, pipelineKindOf, type PipelineKind } from '../pipelineKinds'
import { useCurrentProject } from '../composables/useCurrentProject'
import { usePetStore } from '../stores/pet'

const { t } = useI18n()
const router = useRouter()
const { currentProjectId, setCurrentProjectId, refreshProjects } = useCurrentProject()
const pet = usePetStore()
const list = ref<any[]>([])
const projects = ref<any[]>([])
const loading = ref(false)
const creating = ref(false)
const creatingProject = ref(false)
const showNewProject = ref(false)

const kinds = PIPELINE_KINDS
const form = reactive({ name: '', project_id: '', description: '', kind: 'api' })
const projectForm = reactive({ name: '', runtime_base_url: 'https://httpbin.org', description: '' })

function stepLabel(step: string) {
  if (step === 'cases') return t('pipelineHub.stepCases')
  if (step === 'report') return t('pipelineHub.stepReport')
  return t('pipelineHub.stepReq')
}

function kindLabel(kind: string) {
  return t(pipelineKindOf(kind).titleKey)
}

function selectKind(k: PipelineKind) {
  if (!k.available) {
    ElMessage.info(t('pipelineHub.comingSoonHint', { name: t(k.titleKey) }))
    return
  }
  form.kind = k.id
}

async function load() {
  loading.value = true
  try {
    ;[list.value, projects.value] = await Promise.all([api.listPipelines(), api.listProjects()])
    if (currentProjectId.value && projects.value.some((p) => p.id === currentProjectId.value)) {
      form.project_id = currentProjectId.value
    } else if (!form.project_id && projects.value[0]) {
      form.project_id = projects.value[0].id
    }
  } finally {
    loading.value = false
  }
}

async function createProjectQuick() {
  if (!projectForm.name.trim()) {
    ElMessage.warning(t('pipelineHub.warnProjectName'))
    return
  }
  creatingProject.value = true
  try {
    const row = await api.createProject(projectForm)
    projects.value = await api.listProjects()
    form.project_id = row.id
    setCurrentProjectId(row.id)
    await refreshProjects()
    pet.completeQuest('create_project')
    showNewProject.value = false
    ElMessage.success(t('pipelineHub.createdProject', { name: row.name }))
  } finally {
    creatingProject.value = false
  }
}

async function create() {
  if (!form.name.trim() || !form.project_id) {
    ElMessage.warning(t('pipelineHub.warnNameProject'))
    return
  }
  creating.value = true
  try {
    const row = await api.createPipeline({
      name: form.name.trim(),
      project_id: form.project_id,
      description: form.description,
      kind: form.kind,
      step: 'req',
    })
    setCurrentProjectId(form.project_id)
    pet.completeQuest('create_pipeline')
    router.push(`/pipelines/${row.id}`)
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.kind-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
}
.kind-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  text-align: left;
  min-height: 118px;
  padding: 14px 14px 12px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.72);
  font: inherit;
  color: inherit;
  cursor: pointer;
  transition: border-color 0.15s ease, transform 0.15s ease;
}
.kind-card:hover:not(:disabled) {
  transform: translateY(-2px);
  border-color: rgba(15, 143, 134, 0.45);
}
.kind-card.active {
  border-color: rgba(15, 143, 134, 0.7);
  background: rgba(15, 143, 134, 0.08);
  box-shadow: 0 0 0 1px rgba(15, 143, 134, 0.2);
}
.kind-card.disabled,
.kind-card:disabled {
  cursor: not-allowed;
  opacity: 0.62;
  background: rgba(247, 250, 251, 0.9);
}
.kind-ico {
  font-size: 18px;
  line-height: 1;
  color: var(--teal-deep);
}
.kind-card strong {
  font-family: var(--font-brand);
  font-size: 15px;
}
.kind-card small {
  color: var(--mute);
  font-size: 12px;
  line-height: 1.4;
}
.soon {
  margin-top: auto;
  font-size: 11px;
  font-weight: 650;
  color: var(--teal-deep);
}
.top { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.status-pill.soft { background: rgba(15, 40, 50, 0.06); color: var(--ink-soft); }

.create { padding: 22px 24px; margin-bottom: 22px; }
.create-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-bottom: 16px; }
.kicker { font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--teal-deep); font-weight: 650; }
.create-head h3 { margin: 4px 0 0; font-family: var(--font-brand); font-size: 20px; }
.hint { margin: 0; color: var(--mute); font-size: 13px; max-width: 360px; text-align: right; }
.fields { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 16px; }
.span-2 { grid-column: 1 / -1; }
.project-row { display: flex; gap: 8px; width: 100%; }
.inline-project { margin: 4px 0 16px; padding: 14px 16px; border-radius: 12px; border: 1px dashed var(--line-strong); background: rgba(15, 143, 134, 0.04); }
.inline-title { font-weight: 650; margin-bottom: 8px; font-family: var(--font-brand); }
.actions { display: flex; justify-content: flex-end; margin-top: 4px; }
.list-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 12px; }
.list-head h3 { margin: 0; font-family: var(--font-brand); font-size: 18px; }
.count { font-family: var(--font-mono); font-size: 12px; color: var(--mute); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; min-height: 40px; }
.tile { text-align: left; border: 1px solid var(--line); border-radius: 18px; padding: 18px; background: linear-gradient(160deg, rgba(255,255,255,0.94), rgba(235,247,246,0.75)); box-shadow: var(--shadow-soft); cursor: pointer; transition: transform 0.2s ease, border-color 0.2s ease; font: inherit; color: inherit; min-height: 180px; display: flex; flex-direction: column; }
.tile:hover { transform: translateY(-3px); border-color: rgba(15, 143, 134, 0.4); }
.mono { color: var(--mute); font-family: var(--font-mono); font-size: 12px; }
.tile h3 { margin: 0; font-family: var(--font-brand); font-size: 20px; }
.tile p { margin: 8px 0 0; color: var(--mute); font-size: 13px; flex: 1; }
.foot { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--line); display: flex; justify-content: space-between; gap: 8px; font-size: 12px; color: var(--ink-soft); }
.go { color: var(--teal-deep); font-weight: 650; }
.empty-hint { color: var(--mute); font-size: 13px; padding: 8px 2px 0; }
@media (max-width: 800px) {
  .fields { grid-template-columns: 1fr; }
  .create-head { flex-direction: column; align-items: flex-start; }
  .hint { text-align: left; }
  .kind-grid { grid-template-columns: 1fr 1fr; }
}
</style>
