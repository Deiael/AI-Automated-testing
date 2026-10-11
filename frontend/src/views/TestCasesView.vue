<template>
  <div class="split">
    <section>
      <div class="toolbar">
        <el-select v-model="templateId" placeholder="用例模板" style="width: 200px">
          <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
        <el-button type="primary" @click="start">新建对话并生成</el-button>
      </div>
      <ChatPanel v-if="sessionId" :session-id="sessionId" @done="loadCases" @artifact="loadCases" />
      <div v-else class="placeholder panel">
        <h3>按模板生成用例</h3>
        <p>网关会注入项目 RAG 与模板 schema，并计算置信度。</p>
      </div>
    </section>
    <aside class="side panel">
      <div class="side-head">
        <h3>用例列表</h3>
        <span class="count">{{ cases.length }}</span>
      </div>
      <article v-for="row in cases" :key="row.id" class="item">
        <div class="item-top">
          <strong>{{ row.title }}</strong>
          <span class="conf">{{ Number(row.confidence || 0).toFixed(2) }}</span>
        </div>
        <div class="meta">
          <span class="status-pill" :class="row.status === 'CONFIRMED' ? '' : 'warn'">{{ row.status }}</span>
        </div>
        <el-button v-if="row.status !== 'CONFIRMED'" link type="primary" @click="confirm(row)">确认</el-button>
      </article>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import ChatPanel from '../components/ChatPanel.vue'

const route = useRoute()
const pid = String(route.params.id)
const sessionId = ref('')
const templates = ref<any[]>([])
const templateId = ref('')
const cases = ref<any[]>([])

async function loadCases() {
  cases.value = await api.listTestCases(pid)
}

async function start() {
  const s = await api.createSession({
    project_id: pid,
    flow_type: 'TEST_CASE',
    title: '用例生成',
    template_id: templateId.value || null,
  })
  sessionId.value = s.id
}

async function confirm(row: any) {
  await api.patchTestCase(row.id, { status: 'CONFIRMED' })
  ElMessage.success('已确认')
  await loadCases()
}

onMounted(async () => {
  templates.value = await api.listTemplates(pid)
  if (templates.value[0]) templateId.value = templates.value[0].id
  await loadCases()
})
</script>

<style scoped>
.split {
  display: grid;
  grid-template-columns: 1.35fr 0.9fr;
  gap: 16px;
}
.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.placeholder {
  padding: 40px 24px;
  min-height: 320px;
}
.placeholder h3 {
  margin: 0;
  font-family: var(--font-brand);
}
.placeholder p {
  color: var(--mute);
  margin-top: 8px;
}
.side {
  padding: 14px;
  max-height: 700px;
  overflow: auto;
}
.side-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.side-head h3 {
  margin: 0;
  font-family: var(--font-brand);
}
.count {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--mute);
}
.item {
  padding: 12px 0;
  border-top: 1px solid var(--line);
}
.item-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.conf {
  font-family: var(--font-mono);
  color: var(--teal-deep);
  font-weight: 650;
}
.meta {
  margin: 8px 0;
}
@media (max-width: 1000px) {
  .split {
    grid-template-columns: 1fr;
  }
}
</style>
