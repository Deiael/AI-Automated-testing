<template>
  <div class="openapi panel-inner">
    <div class="head">
      <div>
        <div class="kicker">OpenAPI</div>
        <h4>{{ t('openapi.title') }}</h4>
        <p>{{ t('openapi.tip') }}</p>
      </div>
      <el-button type="primary" :loading="importing" @click="doImport">{{ t('openapi.import') }}</el-button>
    </div>

    <el-form label-position="top" class="form">
      <div class="row">
        <el-form-item :label="t('openapi.url')">
          <el-input v-model="url" :placeholder="t('openapi.urlPh')" />
        </el-form-item>
        <el-form-item :label="t('openapi.orFile')">
          <el-upload :auto-upload="false" :show-file-list="!!fileName" :on-change="onFile" :limit="1">
            <el-button>{{ t('openapi.pick') }}</el-button>
          </el-upload>
        </el-form-item>
      </div>
      <el-form-item :label="t('openapi.paste')">
        <el-input v-model="content" type="textarea" :rows="5" :placeholder="t('openapi.pastePh')" />
      </el-form-item>
      <el-checkbox v-model="confirm">{{ t('openapi.autoConfirm') }}</el-checkbox>
    </el-form>

    <div v-if="lastResult" class="result">
      <strong>{{ t('openapi.result', { ops: lastResult.operations, points: lastResult.points_created, cases: lastResult.cases_created }) }}</strong>
    </div>

    <div v-if="specs.length" class="specs">
      <div class="block-title">{{ t('openapi.specs') }}</div>
      <article v-for="s in specs" :key="s.id" class="spec">
        <div>
          <strong>{{ s.title }}</strong>
          <div class="meta">{{ s.version || '—' }} · {{ s.operations_count }} ops · {{ s.source }}</div>
        </div>
        <el-button link type="danger" @click="removeSpec(s.id)">{{ t('common.delete') }}</el-button>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps<{ projectId: string; pipelineId?: string }>()
const emit = defineEmits<{ imported: [] }>()
const { t } = useI18n()

const url = ref('')
const content = ref('')
const file = ref<File | null>(null)
const fileName = ref('')
const confirm = ref(true)
const importing = ref(false)
const specs = ref<any[]>([])
const lastResult = ref<any>(null)

function onFile(f: any) {
  file.value = f.raw
  fileName.value = f.name
}

async function loadSpecs() {
  if (!props.projectId) return
  specs.value = await api.listApiSpecs(props.projectId, props.pipelineId)
}

async function doImport() {
  if (!url.value.trim() && !content.value.trim() && !file.value) {
    ElMessage.warning(t('openapi.warnEmpty'))
    return
  }
  importing.value = true
  try {
    const form = new FormData()
    form.append('project_id', props.projectId)
    if (props.pipelineId) form.append('pipeline_id', props.pipelineId)
    form.append('create_artifacts', 'true')
    form.append('confirm', String(confirm.value))
    if (file.value) form.append('file', file.value)
    else if (content.value.trim()) form.append('content', content.value)
    else form.append('url', url.value.trim())
    lastResult.value = await api.importOpenApi(form)
    ElMessage.success(t('openapi.ok'))
    url.value = ''
    content.value = ''
    file.value = null
    fileName.value = ''
    await loadSpecs()
    emit('imported')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || t('openapi.fail'))
  } finally {
    importing.value = false
  }
}

async function removeSpec(id: string) {
  await api.deleteApiSpec(id)
  await loadSpecs()
}

onMounted(loadSpecs)
watch(() => [props.projectId, props.pipelineId], loadSpecs)
</script>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 12px;
}
.kicker {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}
h4 {
  margin: 4px 0;
}
p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}
.row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
}
.result {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(18, 143, 135, 0.08);
}
.specs {
  margin-top: 16px;
}
.spec {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
}
.meta {
  font-size: 12px;
  color: var(--muted);
  margin-top: 2px;
}
.block-title {
  font-weight: 700;
  margin-bottom: 6px;
}
</style>
