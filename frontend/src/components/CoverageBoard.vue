<template>
  <div class="coverage" v-loading="loading">
    <div class="head">
      <div>
        <div class="kicker">Coverage</div>
        <h4>{{ t('coverage.title') }}</h4>
        <p>{{ t('coverage.tip') }}</p>
      </div>
      <el-button @click="load">{{ t('coverage.refresh') }}</el-button>
    </div>

    <div class="cards" v-if="board">
      <div class="card">
        <div class="label">{{ t('coverage.api') }}</div>
        <div class="value">{{ pct(board.api?.ratio) }}</div>
        <div class="sub">{{ board.api?.covered || 0 }} / {{ board.api?.total || 0 }}</div>
      </div>
      <div class="card">
        <div class="label">{{ t('coverage.req') }}</div>
        <div class="value">{{ pct(board.requirement?.ratio) }}</div>
        <div class="sub">{{ board.requirement?.covered || 0 }} / {{ board.requirement?.total || 0 }}</div>
      </div>
      <div class="card">
        <div class="label">{{ t('coverage.overall') }}</div>
        <div class="value">{{ pct(board.overall_ratio) }}</div>
        <div class="sub">{{ t('coverage.blend') }}</div>
      </div>
    </div>

    <el-tabs v-model="tab" class="tabs">
      <el-tab-pane :label="t('coverage.apiGaps')" name="api">
        <el-table :data="uncoveredApi" size="small" max-height="280">
          <el-table-column prop="method" :label="t('coverage.method')" width="90" />
          <el-table-column prop="path" :label="t('coverage.path')" />
          <el-table-column prop="summary" :label="t('coverage.summary')" />
        </el-table>
        <el-empty v-if="!uncoveredApi.length" :description="t('coverage.apiFull')" :image-size="48" />
      </el-tab-pane>
      <el-tab-pane :label="t('coverage.reqGaps')" name="req">
        <el-table :data="uncoveredReq" size="small" max-height="280">
          <el-table-column prop="kind" :label="t('coverage.kind')" width="120" />
          <el-table-column prop="title" :label="t('coverage.summary')" />
        </el-table>
        <el-empty v-if="!uncoveredReq.length" :description="t('coverage.reqFull')" :image-size="48" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'

const props = defineProps<{ projectId: string; pipelineId?: string }>()
const { t } = useI18n()
const loading = ref(false)
const board = ref<any>(null)
const tab = ref('api')

const uncoveredApi = computed(() => (board.value?.api?.items || []).filter((i: any) => !i.covered))
const uncoveredReq = computed(() => (board.value?.requirement?.items || []).filter((i: any) => !i.covered))

function pct(v: number | undefined) {
  return `${Math.round(Number(v || 0) * 100)}%`
}

async function load() {
  if (!props.projectId) return
  loading.value = true
  try {
    board.value = await api.getCoverage(props.projectId, props.pipelineId)
  } finally {
    loading.value = false
  }
}

defineExpose({ load })
onMounted(load)
watch(() => [props.projectId, props.pipelineId], load)
</script>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
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
.cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.card {
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.55);
}
.label {
  font-size: 12px;
  color: var(--muted);
}
.value {
  font-size: 28px;
  font-weight: 700;
  margin: 4px 0;
}
.sub {
  font-size: 12px;
  color: var(--muted);
}
</style>
