<template>
  <div class="defect">
    <div class="head">
      <div>
        <div class="kicker">Defects</div>
        <h4>{{ t('defect.title') }}</h4>
        <p>{{ t('defect.tip') }}</p>
      </div>
      <el-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</el-button>
    </div>

    <el-form label-position="top">
      <el-form-item :label="t('defect.enabled')">
        <el-switch v-model="form.enabled" />
      </el-form-item>
      <el-form-item :label="t('defect.provider')">
        <el-select v-model="form.provider" style="width: 200px">
          <el-option label="GitHub Issues" value="github" />
          <el-option label="Webhook" value="webhook" />
        </el-select>
      </el-form-item>
      <template v-if="form.provider === 'github'">
        <el-form-item :label="t('defect.repo')">
          <el-input v-model="form.repo" placeholder="owner/repo" />
        </el-form-item>
        <el-form-item :label="t('defect.token')">
          <el-input v-model="form.token" type="password" show-password :placeholder="t('defect.tokenPh')" />
        </el-form-item>
      </template>
      <el-form-item v-else :label="t('defect.webhook')">
        <el-input v-model="form.webhook_url" placeholder="https://..." />
      </el-form-item>
    </el-form>

    <div class="block-title">{{ t('defect.recent') }}</div>
    <el-table :data="issues" size="small" max-height="240">
      <el-table-column prop="title" :label="t('defect.issueTitle')" />
      <el-table-column prop="status" :label="t('common.status')" width="90" />
      <el-table-column :label="t('defect.link')" width="90">
        <template #default="{ row }">
          <a v-if="row.external_url" :href="row.external_url" target="_blank" rel="noreferrer">open</a>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps<{ projectId: string; pipelineId?: string }>()
const { t } = useI18n()
const saving = ref(false)
const issues = ref<any[]>([])
const form = reactive({
  enabled: false,
  provider: 'github',
  token: '',
  repo: '',
  webhook_url: '',
  labels: ['ai-test', 'auto'],
})

async function load() {
  if (!props.projectId) return
  const cfg = await api.getDefectConfig(props.projectId)
  form.enabled = !!cfg.enabled
  form.provider = cfg.provider || 'github'
  form.token = cfg.token || ''
  form.repo = cfg.repo || ''
  form.webhook_url = cfg.webhook_url || ''
  form.labels = cfg.labels || ['ai-test', 'auto']
  issues.value = await api.listDefects(props.projectId, props.pipelineId)
}

async function save() {
  saving.value = true
  try {
    await api.putDefectConfig(props.projectId, { ...form })
    ElMessage.success(t('defect.saved'))
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || t('defect.fail'))
  } finally {
    saving.value = false
  }
}

onMounted(load)
watch(() => props.projectId, load)
</script>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
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
.block-title {
  font-weight: 700;
  margin: 16px 0 8px;
}
</style>
