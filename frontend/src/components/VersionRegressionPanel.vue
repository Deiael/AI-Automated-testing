<template>
  <div class="vreg">
    <div class="head">
      <div>
        <div class="kicker">Version regression</div>
        <h4>{{ t('vreg.title') }}</h4>
        <p>{{ t('vreg.tip') }}</p>
      </div>
    </div>

    <el-form label-position="top" class="form">
      <div class="row">
        <el-form-item :label="t('vreg.oldName')">
          <el-input v-model="baselineName" :placeholder="t('vreg.oldNamePh')" />
        </el-form-item>
        <el-form-item :label="' '">
          <el-button :loading="saving" @click="saveOld">{{ t('vreg.saveOld') }}</el-button>
        </el-form-item>
      </div>
      <el-form-item :label="t('vreg.pickOld')">
        <el-select v-model="baselineId" :placeholder="t('vreg.pickOldPh')" style="width: 100%" clearable>
          <el-option
            v-for="b in baselines"
            :key="b.id"
            :label="`${b.name} · ${b.operations} ops · ${formatTime(b.created_at)}`"
            :value="b.id"
          />
        </el-select>
      </el-form-item>
    </el-form>

    <div class="actions">
      <el-button :disabled="!baselineId" :loading="planning" @click="analyze">{{ t('vreg.analyze') }}</el-button>
      <el-button type="primary" :disabled="!baselineId" :loading="generating" @click="generate(false)">
        {{ t('vreg.generate') }}
      </el-button>
      <el-button type="primary" plain :disabled="!baselineId" :loading="running" @click="generate(true)">
        {{ t('vreg.generateRun') }}
      </el-button>
    </div>

    <div v-if="plan" class="tracks">
      <div class="track">
        <strong>{{ t('vreg.predict') }}</strong>
        <p>{{ t('vreg.predictTip') }} · {{ (plan.predict || []).length }}</p>
        <ul>
          <li v-for="(item, i) in (plan.predict || []).slice(0, 8)" :key="'p' + i">{{ item.reason }} · {{ item.key }}</li>
        </ul>
        <el-empty v-if="!(plan.predict || []).length" :description="t('vreg.noPredict')" :image-size="48" />
      </div>
      <div class="track">
        <strong>{{ t('vreg.localize') }}</strong>
        <p>
          {{ t('vreg.localizeTip') }} · +{{ plan.diff?.added || 0 }} / ~{{ plan.diff?.changed || 0 }} / -{{
            plan.diff?.removed || 0
          }}
        </p>
        <ul>
          <li v-for="(item, i) in (plan.localize || []).slice(0, 8)" :key="'l' + i">{{ item.reason }} · {{ item.key }}</li>
        </ul>
        <el-empty v-if="!(plan.localize || []).length" :description="t('vreg.noLocalize')" :image-size="48" />
      </div>
    </div>

    <div v-if="lastGen" class="result">
      {{
        t('vreg.result', {
          points: lastGen.generated?.points_created || 0,
          cases: lastGen.generated?.cases_created || 0,
        })
      }}
      <span v-if="lastGen.run?.summary">
        · {{ t('vreg.runResult', { passed: lastGen.run.summary.passed ?? 0, failed: lastGen.run.summary.failed ?? 0 }) }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps<{ projectId: string; pipelineId: string }>()
const emit = defineEmits<{ generated: []; ran: [] }>()
const { t } = useI18n()

const baselines = ref<any[]>([])
const baselineId = ref('')
const baselineName = ref('v1')
const saving = ref(false)
const planning = ref(false)
const generating = ref(false)
const running = ref(false)
const plan = ref<any>(null)
const lastGen = ref<any>(null)

function formatTime(v: string) {
  if (!v) return ''
  try {
    return new Date(v).toLocaleString()
  } catch {
    return String(v)
  }
}

async function load() {
  if (!props.projectId) return
  baselines.value = await api.listBaselines(props.projectId, props.pipelineId)
  if (!baselineId.value && baselines.value[0]) baselineId.value = baselines.value[0].id
}

async function saveOld() {
  saving.value = true
  try {
    const row = await api.createBaseline({
      project_id: props.projectId,
      pipeline_id: props.pipelineId,
      name: baselineName.value || 'v1',
    })
    ElMessage.success(t('vreg.saved'))
    await load()
    baselineId.value = row.id
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || t('vreg.fail'))
  } finally {
    saving.value = false
  }
}

async function analyze() {
  planning.value = true
  try {
    plan.value = await api.regressionPlan({
      project_id: props.projectId,
      pipeline_id: props.pipelineId,
      baseline_id: baselineId.value,
    })
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || t('vreg.fail'))
  } finally {
    planning.value = false
  }
}

async function generate(execute: boolean) {
  if (execute) running.value = true
  else generating.value = true
  try {
    lastGen.value = await api.regressionGenerate({
      project_id: props.projectId,
      pipeline_id: props.pipelineId,
      baseline_id: baselineId.value,
      confirm: true,
      execute,
    })
    plan.value = lastGen.value.plan
    ElMessage.success(execute ? t('vreg.runOk') : t('vreg.genOk'))
    emit('generated')
    if (execute) emit('ran')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || t('vreg.fail'))
  } finally {
    generating.value = false
    running.value = false
  }
}

onMounted(load)
watch(() => [props.projectId, props.pipelineId], load)
</script>

<style scoped>
.head {
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
  align-items: end;
}
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 8px 0 14px;
}
.tracks {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.track {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.55);
}
.track ul {
  margin: 8px 0 0;
  padding-left: 18px;
  font-size: 12px;
  color: var(--muted);
}
.result {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(18, 143, 135, 0.08);
  font-size: 13px;
}
</style>
