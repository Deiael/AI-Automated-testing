<template>
  <div class="split">
    <section>
      <div class="toolbar">
        <el-button type="primary" @click="start">新建对话并生成</el-button>
        <el-select v-model="engineId" clearable placeholder="覆盖引擎" style="width: 220px">
          <el-option v-for="e in engines" :key="e.id" :label="e.name" :value="e.id" />
        </el-select>
      </div>
      <ChatPanel
        v-if="sessionId"
        :session-id="sessionId"
        :engine-profile-id="engineId || undefined"
        @artifact="onArt"
        @done="loadPoints"
      />
      <div v-else class="placeholder panel">
        <h3>从对话开始</h3>
        <p>创建会话后，可多轮修订测试点，再在右侧确认落库。</p>
      </div>
    </section>
    <aside class="side panel">
      <div class="side-head">
        <h3>测试点列表</h3>
        <span class="count">{{ points.length }}</span>
      </div>
      <div v-if="!points.length" class="empty">暂无产物</div>
      <article v-for="row in points" :key="row.id" class="item">
        <div class="item-top">
          <strong>{{ row.title }}</strong>
          <span class="status-pill" :class="row.status === 'CONFIRMED' ? '' : 'warn'">{{ row.status }}</span>
        </div>
        <p>{{ row.content_json?.description || '—' }}</p>
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
const engineId = ref('')
const engines = ref<any[]>([])
const points = ref<any[]>([])

async function loadPoints() {
  points.value = await api.listTestPoints(pid)
}

async function start() {
  const s = await api.createSession({
    project_id: pid,
    flow_type: 'TEST_POINT',
    title: '测试点生成',
    engine_profile_id: engineId.value || null,
  })
  sessionId.value = s.id
}

async function confirm(row: any) {
  await api.patchTestPoint(row.id, { status: 'CONFIRMED' })
  ElMessage.success('已确认')
  await loadPoints()
}

function onArt() {
  loadPoints()
}

onMounted(async () => {
  engines.value = await api.listEngines()
  await loadPoints()
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
  align-items: flex-start;
}
.item p {
  margin: 6px 0 8px;
  color: var(--mute);
  font-size: 13px;
  line-height: 1.5;
}
.empty {
  color: var(--mute);
  font-size: 13px;
  padding: 20px 0;
}
@media (max-width: 1000px) {
  .split {
    grid-template-columns: 1fr;
  }
}
</style>
