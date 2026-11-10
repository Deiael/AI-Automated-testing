<template>
  <div class="panel form-wrap" v-if="project">
    <el-form label-position="top" class="form">
      <el-form-item :label="t('overview.desc')">
        <el-input v-model="form.description" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item :label="t('overview.envs')">
        <p class="hint">{{ t('overview.envsTip') }}</p>
        <div v-for="(env, idx) in envs" :key="env.id" class="env-row">
          <el-input v-model="env.name" :placeholder="t('overview.envName')" style="width: 110px" />
          <el-input v-model="env.base_url" placeholder="https://api-test.example.com" />
          <el-input-number v-model="env.timeout_sec" :min="5" :max="180" controls-position="right" style="width: 110px" />
          <el-radio :model-value="env.is_default" @change="setDefault(idx)">{{ t('overview.envDefault') }}</el-radio>
          <el-button link type="danger" :disabled="envs.length <= 1" @click="envs.splice(idx, 1)">{{ t('common.delete') }}</el-button>
        </div>
        <el-button plain @click="addEnv">{{ t('overview.addEnv') }}</el-button>
      </el-form-item>
      <el-form-item :label="t('overview.headers')">
        <el-input v-model="headersText" type="textarea" :rows="2" placeholder='{"Authorization":"Bearer {{token}}"}' />
      </el-form-item>
      <el-form-item :label="t('overview.variables')">
        <el-input
          v-model="variablesText"
          type="textarea"
          :rows="4"
          :placeholder="t('overview.variablesPh')"
        />
      </el-form-item>
      <el-form-item :label="t('overview.engine')">
        <el-select v-model="form.engine_profile_id" clearable style="width: 100%">
          <el-option v-for="e in engines" :key="e.id" :label="`${e.name} (${e.model})`" :value="e.id" />
        </el-select>
      </el-form-item>
      <el-button type="primary" @click="save">{{ t('overview.save') }}</el-button>
    </el-form>

    <DefectConfigPanel v-if="projectId" class="defect-block" :project-id="projectId" />
  </div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import DefectConfigPanel from '../components/DefectConfigPanel.vue'

const { t } = useI18n()
const project = inject<any>('project')
const engines = ref<any[]>([])
const variablesText = ref('{}')
const headersText = ref('{}')
const envs = ref<any[]>([])
const form = reactive({
  description: '',
  runtime_base_url: '',
  engine_profile_id: '' as string | null,
})

function addEnv() {
  envs.value.push({
    id: crypto.randomUUID?.() || String(Date.now()),
    name: `env-${envs.value.length + 1}`,
    base_url: form.runtime_base_url || '',
    headers: {},
    variables: {},
    timeout_sec: 30,
    is_default: envs.value.length === 0,
  })
}

function setDefault(idx: number) {
  envs.value.forEach((e, i) => {
    e.is_default = i === idx
  })
}
const projectId = computed(() => {
  const p = project?.value || project
  return p?.id || ''
})

watch(
  project,
  (p) => {
    if (!p) return
    const row = p.value || p
    if (!row?.id) return
    form.description = row.description || ''
    form.runtime_base_url = row.runtime_base_url || ''
    form.engine_profile_id = row.engine_profile_id || null
    variablesText.value = JSON.stringify(row.runtime_variables || {}, null, 2)
    headersText.value = JSON.stringify(row.runtime_headers || {}, null, 2)
    const listed = Array.isArray(row.runtime_envs) ? row.runtime_envs.filter((e: any) => e) : []
    envs.value = listed.length
      ? listed.map((e: any) => ({
          id: e.id || crypto.randomUUID?.() || String(Date.now()),
          name: e.name || 'default',
          base_url: e.base_url || '',
          headers: e.headers || {},
          variables: e.variables || {},
          timeout_sec: e.timeout_sec || 30,
          is_default: !!e.is_default,
        }))
      : [
          {
            id: 'default',
            name: 'default',
            base_url: row.runtime_base_url || '',
            headers: row.runtime_headers || {},
            variables: row.runtime_variables || {},
            timeout_sec: 30,
            is_default: true,
          },
        ]
  },
  { immediate: true, deep: true },
)

onMounted(async () => {
  engines.value = await api.listEngines()
})

async function save() {
  const row = project?.value || project
  let runtime_variables: Record<string, any> = {}
  try {
    const parsed = JSON.parse(variablesText.value || '{}')
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('bad')
    }
    runtime_variables = parsed
  } catch {
    ElMessage.error(t('caseEditor.badJson'))
    return
  }
  let runtime_headers: Record<string, any> = {}
  try {
    const parsed = JSON.parse(headersText.value || '{}')
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('bad')
    runtime_headers = parsed
  } catch {
    ElMessage.error(t('caseEditor.badJson'))
    return
  }
  const runtime_envs = envs.value.map((e, i) => ({
    ...e,
    headers: i === 0 ? runtime_headers : e.headers || {},
    variables: i === 0 ? runtime_variables : e.variables || {},
  }))
  const def = runtime_envs.find((e) => e.is_default) || runtime_envs[0]
  await api.updateProject(row.id, {
    name: row.name,
    description: form.description,
    runtime_base_url: def?.base_url || form.runtime_base_url,
    runtime_headers,
    runtime_variables,
    runtime_envs,
    engine_profile_id: form.engine_profile_id,
  })
  ElMessage.success(t('overview.saved'))
  Object.assign(row, form, { runtime_variables, runtime_headers, runtime_envs, runtime_base_url: def?.base_url })
}
</script>

<style scoped>
.form-wrap {
  padding: 20px 22px;
  max-width: 720px;
}
.defect-block {
  margin-top: 28px;
  padding-top: 18px;
  border-top: 1px solid var(--line);
}
.hint {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--muted);
}
.env-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.env-row :deep(.el-input) {
  flex: 1;
}
</style>
