<template>
  <div class="panel form-wrap" v-if="project">
    <el-form label-position="top" class="form">
      <el-form-item :label="t('overview.desc')">
        <el-input v-model="form.description" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item :label="t('overview.baseUrl')">
        <el-input v-model="form.runtime_base_url" />
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
const form = reactive({
  description: '',
  runtime_base_url: '',
  engine_profile_id: '' as string | null,
})
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
  await api.updateProject(row.id, {
    name: row.name,
    description: form.description,
    runtime_base_url: form.runtime_base_url,
    runtime_headers: row.runtime_headers || {},
    runtime_variables,
    engine_profile_id: form.engine_profile_id,
  })
  ElMessage.success(t('overview.saved'))
  Object.assign(row, form, { runtime_variables })
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
</style>
