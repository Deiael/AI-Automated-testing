<template>
  <div class="sched">
    <div class="head">
      <div>
        <div class="kicker">CI / Schedule</div>
        <h4>{{ t('schedule.title') }}</h4>
        <p>{{ t('schedule.tip') }}</p>
      </div>
      <div class="actions">
        <el-button :loading="runningCi" type="primary" plain @click="runCi">{{ t('schedule.runNow') }}</el-button>
        <el-button type="primary" :loading="creating" @click="create">{{ t('schedule.add') }}</el-button>
      </div>
    </div>

    <el-form inline class="form">
      <el-form-item :label="t('schedule.name')">
        <el-input v-model="form.name" style="width: 140px" />
      </el-form-item>
      <el-form-item :label="t('schedule.cron')">
        <el-select v-model="form.cron" style="width: 160px">
          <el-option :label="t('schedule.hourly')" value="hourly" />
          <el-option :label="t('schedule.daily')" value="daily" />
          <el-option :label="t('schedule.weekly')" value="weekly" />
        </el-select>
      </el-form-item>
    </el-form>

    <el-table :data="jobs" size="small" v-loading="loading">
      <el-table-column prop="name" :label="t('schedule.name')" />
      <el-table-column prop="cron" :label="t('schedule.cron')" width="100" />
      <el-table-column prop="enabled" :label="t('common.status')" width="100">
        <template #default="{ row }">
          <el-switch :model-value="row.enabled" @change="(v: boolean) => toggle(row, v)" />
        </template>
      </el-table-column>
      <el-table-column prop="last_status" :label="t('schedule.lastStatus')" width="110" />
      <el-table-column :label="t('common.actions')" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="runJob(row)">{{ t('schedule.trigger') }}</el-button>
          <el-button link type="danger" @click="remove(row)">{{ t('common.delete') }}</el-button>
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

const props = defineProps<{ projectId: string; pipelineId: string }>()
const emit = defineEmits<{ ran: [] }>()
const { t } = useI18n()
const jobs = ref<any[]>([])
const loading = ref(false)
const creating = ref(false)
const runningCi = ref(false)
const form = reactive({ name: 'regression', cron: 'daily' })

async function load() {
  if (!props.projectId) return
  loading.value = true
  try {
    jobs.value = await api.listSchedules(props.projectId, props.pipelineId)
  } finally {
    loading.value = false
  }
}

async function create() {
  creating.value = true
  try {
    await api.createSchedule({
      project_id: props.projectId,
      pipeline_id: props.pipelineId,
      name: form.name || 'regression',
      cron: form.cron,
      enabled: true,
    })
    ElMessage.success(t('schedule.created'))
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || t('schedule.fail'))
  } finally {
    creating.value = false
  }
}

async function toggle(row: any, enabled: boolean) {
  await api.patchSchedule(row.id, { enabled })
  await load()
}

async function remove(row: any) {
  await api.deleteSchedule(row.id)
  await load()
}

async function runJob(row: any) {
  try {
    await api.runSchedule(row.id)
    ElMessage.success(t('schedule.triggered'))
    emit('ran')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || t('schedule.fail'))
  }
}

async function runCi() {
  runningCi.value = true
  try {
    const res = await api.ciRun({
      project_id: props.projectId,
      pipeline_id: props.pipelineId,
      trigger: 'ui',
    })
    ElMessage.success(t('schedule.ciOk', { passed: res.summary?.passed ?? 0, failed: res.summary?.failed ?? 0 }))
    emit('ran')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || t('schedule.fail'))
  } finally {
    runningCi.value = false
  }
}

onMounted(load)
watch(() => [props.projectId, props.pipelineId], load)
</script>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.actions {
  display: flex;
  gap: 8px;
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
</style>
