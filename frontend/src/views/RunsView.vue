<template>
  <div class="stack">
    <div class="toolbar">
      <el-button type="primary" @click="start">对已确认用例发起执行</el-button>
    </div>
    <ChatPanel v-if="sessionId" :session-id="sessionId" @artifact="onArt" @done="reload" />
    <div v-else class="placeholder panel">
      <h3>执行与报告</h3>
      <p>引擎按用例发起 HTTP 请求，结果回传网关持久化。</p>
    </div>

    <div class="two">
      <div class="panel block">
        <h3>执行记录</h3>
        <el-table :data="runs" size="small">
          <el-table-column prop="id" label="Run ID" />
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column label="用例数" width="100">
            <template #default="{ row }">{{ (row.case_ids_json || []).length }}</template>
          </el-table-column>
        </el-table>
      </div>
      <div class="panel block">
        <h3>报告</h3>
        <el-table :data="reports" size="small">
          <el-table-column prop="id" label="Report ID" />
          <el-table-column prop="run_id" label="Run" />
          <el-table-column label="摘要">
            <template #default="{ row }">{{ JSON.stringify(row.summary_json) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import ChatPanel from '../components/ChatPanel.vue'

const route = useRoute()
const pid = String(route.params.id)
const sessionId = ref('')
const runs = ref<any[]>([])
const reports = ref<any[]>([])

async function reload() {
  runs.value = await api.listRuns(pid)
  reports.value = await api.listReports()
}

async function start() {
  const s = await api.createSession({ project_id: pid, flow_type: 'TEST_EXECUTE', title: '执行' })
  sessionId.value = s.id
}

function onArt() {
  reload()
}

onMounted(reload)
</script>

<style scoped>
.stack {
  display: grid;
  gap: 14px;
}
.toolbar {
  display: flex;
}
.placeholder {
  padding: 36px 22px;
}
.placeholder h3 {
  margin: 0;
  font-family: var(--font-brand);
}
.placeholder p {
  color: var(--mute);
  margin-top: 8px;
}
.two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.block {
  padding: 14px;
}
.block h3 {
  margin: 0 0 10px;
  font-family: var(--font-brand);
  font-size: 16px;
}
@media (max-width: 1000px) {
  .two {
    grid-template-columns: 1fr;
  }
}
</style>
