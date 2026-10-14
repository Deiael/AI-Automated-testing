<template>
  <div class="rag">
    <div class="toolbar panel">
      <div class="meta">
        <span class="pill">{{ t('rag.store') }}: {{ meta.vector_store || '—' }}</span>
        <span class="pill" v-if="meta.embedding_configured">Embedding: {{ meta.embedding_model }}</span>
        <span class="pill mute" v-else>{{ t('rag.localEmbed') }}</span>
      </div>
      <el-select v-model="kbId" style="width: 240px" :placeholder="t('rag.selectKb')" @change="onKbChange">
        <el-option v-for="k in kbs" :key="k.id" :label="kbLabel(k)" :value="k.id" />
      </el-select>
      <el-button @click="showKbDialog = true">{{ t('rag.newKb') }}</el-button>
    </div>

    <el-tabs v-model="tab" class="tabs">
      <el-tab-pane :label="t('rag.tabDocs')" name="docs">
        <div class="grid-2">
          <div class="panel">
            <h4>{{ t('rag.uploadTitle') }}</h4>
            <el-form label-position="top">
              <el-form-item :label="t('rag.docTitle')">
                <el-input v-model="title" />
              </el-form-item>
              <el-form-item :label="t('rag.strategy')">
                <el-select v-model="strategy" style="width: 100%">
                  <el-option v-for="s in strategies" :key="s.id" :label="`${s.label} — ${s.desc}`" :value="s.id" />
                </el-select>
              </el-form-item>
              <div class="row">
                <el-form-item :label="t('rag.chunkSize')" style="flex: 1">
                  <el-input-number v-model="chunkSize" :min="64" :max="4000" :step="50" />
                </el-form-item>
                <el-form-item :label="t('rag.chunkOverlap')" style="flex: 1">
                  <el-input-number v-model="chunkOverlap" :min="0" :max="2000" :step="10" />
                </el-form-item>
              </div>
              <el-form-item :label="t('rag.content')">
                <el-input v-model="content" type="textarea" :rows="8" :placeholder="t('rag.contentPh')" />
              </el-form-item>
              <div class="actions">
                <el-upload :auto-upload="false" :show-file-list="false" :on-change="onFile">
                  <el-button>{{ t('rag.pickFile') }}</el-button>
                </el-upload>
                <el-button @click="doPreview" :disabled="!content.trim()">{{ t('rag.preview') }}</el-button>
                <el-button type="primary" :loading="uploading" @click="upload">{{ t('rag.index') }}</el-button>
              </div>
            </el-form>
          </div>
          <div class="panel">
            <h4>{{ t('rag.docList') }}</h4>
            <el-table :data="docs" size="small" @row-click="openDoc">
              <el-table-column prop="title" :label="t('rag.docTitle')" />
              <el-table-column prop="chunk_strategy" :label="t('rag.strategy')" width="100" />
              <el-table-column prop="chunk_count" :label="t('rag.chunks')" width="70" />
              <el-table-column prop="status" :label="t('common.status')" width="90" />
              <el-table-column :label="t('common.actions')" width="90">
                <template #default="{ row }">
                  <el-button link type="danger" @click.stop="removeDoc(row.id)">{{ t('common.delete') }}</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="actions" style="margin-top: 10px">
              <el-button size="small" :disabled="!kbId" :loading="reindexing" @click="reindex">{{ t('rag.reindex') }}</el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="t('rag.tabPreview')" name="preview">
        <div class="panel">
          <div class="preview-head">
            <span>{{ t('rag.previewCount', { n: previewChunks.length }) }}</span>
            <el-button size="small" @click="doPreview" :disabled="!content.trim()">{{ t('rag.refreshPreview') }}</el-button>
          </div>
          <div v-if="!previewChunks.length" class="empty">{{ t('rag.previewEmpty') }}</div>
          <div class="chunks">
            <div v-for="c in previewChunks" :key="c.index" class="chunk-card">
              <div class="chunk-meta">
                <b>#{{ c.index + 1 }}</b>
                <span>{{ c.char_count }} chars</span>
                <span v-if="c.section" class="sec">{{ c.section }}</span>
                <span class="range">{{ c.start }}–{{ c.end }}</span>
              </div>
              <pre>{{ c.text }}</pre>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="t('rag.tabSearch')" name="search">
        <div class="panel">
          <div class="row">
            <el-input v-model="searchQ" :placeholder="t('rag.searchPh')" @keydown.enter="doSearch" />
            <el-input-number v-model="searchTopK" :min="1" :max="20" />
            <el-button type="primary" :loading="searching" @click="doSearch">{{ t('rag.search') }}</el-button>
          </div>
          <div class="hits">
            <div v-for="(h, i) in searchHits" :key="h.chunk_id || i" class="chunk-card">
              <div class="chunk-meta">
                <b>{{ h.title || h.doc_id }}</b>
                <span>score {{ Number(h.score).toFixed(4) }}</span>
                <span v-if="h.section" class="sec">{{ h.section }}</span>
              </div>
              <pre>{{ h.text }}</pre>
            </div>
            <div v-if="searched && !searchHits.length" class="empty">{{ t('rag.noHits') }}</div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="t('rag.tabEval')" name="eval">
        <div class="grid-2">
          <div class="panel">
            <h4>{{ t('rag.evalAdd') }}</h4>
            <el-form label-position="top">
              <el-form-item :label="t('rag.evalQuery')">
                <el-input v-model="evalQuery" type="textarea" :rows="2" />
              </el-form-item>
              <el-form-item :label="t('rag.evalKeywords')">
                <el-input v-model="evalKeywords" :placeholder="t('rag.evalKeywordsPh')" />
              </el-form-item>
              <el-form-item :label="t('rag.evalDocIds')">
                <el-select v-model="evalDocIds" multiple filterable style="width: 100%" :placeholder="t('rag.evalDocIdsPh')">
                  <el-option v-for="d in docs" :key="d.id" :label="d.title" :value="d.id" />
                </el-select>
              </el-form-item>
              <el-button type="primary" @click="addEvalCase">{{ t('common.create') }}</el-button>
            </el-form>
            <el-table :data="evalCases" size="small" style="margin-top: 12px">
              <el-table-column prop="query" :label="t('rag.evalQuery')" />
              <el-table-column :label="t('common.actions')" width="80">
                <template #default="{ row }">
                  <el-button link type="danger" @click="removeEval(row.id)">{{ t('common.delete') }}</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div class="panel">
            <div class="preview-head">
              <h4>{{ t('rag.evalRun') }}</h4>
              <el-button type="primary" :loading="evalRunning" :disabled="!kbId" @click="runEval">{{ t('rag.evalStart') }}</el-button>
            </div>
            <div v-if="evalResult" class="eval-summary">
              <div class="stat"><b>{{ (evalResult.hit_at_k * 100).toFixed(1) }}%</b><span>Hit@{{ evalResult.top_k }}</span></div>
              <div class="stat"><b>{{ (evalResult.keyword_recall * 100).toFixed(1) }}%</b><span>{{ t('rag.keywordRecall') }}</span></div>
              <div class="stat"><b>{{ evalResult.total }}</b><span>{{ t('rag.evalCases') }}</span></div>
            </div>
            <div v-for="c in evalResult?.cases || []" :key="c.id" class="chunk-card" :class="{ hit: c.hit, miss: !c.hit }">
              <div class="chunk-meta">
                <b>{{ c.hit ? 'HIT' : 'MISS' }}</b>
                <span>{{ c.query }}</span>
                <span>kw {{ (c.keyword_recall * 100).toFixed(0) }}%</span>
              </div>
              <div class="hit-list">
                <div v-for="(r, i) in c.retrieved" :key="i" class="hit-line">
                  {{ r.title }} · {{ Number(r.score).toFixed(3) }} — {{ r.preview }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="showKbDialog" :title="t('rag.newKb')" width="480px">
      <el-form label-position="top">
        <el-form-item :label="t('common.name')">
          <el-input v-model="kbForm.name" />
        </el-form-item>
        <el-form-item :label="t('rag.kbDesc')">
          <el-input v-model="kbForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item :label="t('rag.strategy')">
          <el-select v-model="kbForm.chunk_strategy" style="width: 100%">
            <el-option v-for="s in strategies" :key="s.id" :label="s.label" :value="s.id" />
          </el-select>
        </el-form-item>
        <div class="row">
          <el-form-item :label="t('rag.chunkSize')" style="flex: 1">
            <el-input-number v-model="kbForm.chunk_size" :min="64" :max="4000" />
          </el-form-item>
          <el-form-item :label="t('rag.chunkOverlap')" style="flex: 1">
            <el-input-number v-model="kbForm.chunk_overlap" :min="0" :max="2000" />
          </el-form-item>
        </div>
        <el-checkbox v-model="kbForm.is_default">{{ t('rag.setDefault') }}</el-checkbox>
      </el-form>
      <template #footer>
        <el-button @click="showKbDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="createKb">{{ t('common.create') }}</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="docDrawer" size="42%" :title="drawerDoc?.title || t('rag.chunks')">
      <div v-if="drawerDoc" class="chunks">
        <div v-for="c in drawerDoc.chunks || []" :key="c.index" class="chunk-card">
          <div class="chunk-meta">
            <b>#{{ (c.index ?? 0) + 1 }}</b>
            <span v-if="c.section" class="sec">{{ c.section }}</span>
          </div>
          <pre>{{ c.text }}</pre>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const { t } = useI18n()
const route = useRoute()
const pid = computed(() => String(route.params.id))

const tab = ref('docs')
const meta = ref<any>({})
const strategies = ref<any[]>([])
const kbs = ref<any[]>([])
const kbId = ref('')
const docs = ref<any[]>([])
const title = ref('')
const content = ref('')
const file = ref<File | null>(null)
const strategy = ref('fixed')
const chunkSize = ref(400)
const chunkOverlap = ref(40)
const uploading = ref(false)
const reindexing = ref(false)
const previewChunks = ref<any[]>([])
const searchQ = ref('')
const searchTopK = ref(5)
const searchHits = ref<any[]>([])
const searching = ref(false)
const searched = ref(false)
const evalCases = ref<any[]>([])
const evalQuery = ref('')
const evalKeywords = ref('')
const evalDocIds = ref<string[]>([])
const evalRunning = ref(false)
const evalResult = ref<any>(null)
const showKbDialog = ref(false)
const kbForm = reactive({
  name: '',
  description: '',
  chunk_strategy: 'fixed',
  chunk_size: 400,
  chunk_overlap: 40,
  is_default: false,
})
const docDrawer = ref(false)
const drawerDoc = ref<any>(null)

function kbLabel(k: any) {
  return `${k.name}${k.is_default ? ' ★' : ''} (${k.doc_count ?? 0})`
}

async function loadMeta() {
  try {
    meta.value = await api.ragMeta(pid.value)
    strategies.value = meta.value.strategies || []
  } catch {
    meta.value = { vector_store: 'mvp', strategies: [] }
    strategies.value = []
  }
}

async function loadKbs() {
  try {
    kbs.value = await api.listRagKbs(pid.value)
    if (!kbId.value && kbs.value.length) kbId.value = kbs.value.find((k: any) => k.is_default)?.id || kbs.value[0].id
    syncStrategyFromKb()
  } catch {
    kbs.value = []
  }
}

function syncStrategyFromKb() {
  const kb = kbs.value.find((k: any) => k.id === kbId.value)
  if (!kb) return
  strategy.value = kb.chunk_strategy || 'fixed'
  chunkSize.value = kb.chunk_size || 400
  chunkOverlap.value = kb.chunk_overlap ?? 40
}

async function loadDocs() {
  if (!kbId.value) {
    docs.value = []
    return
  }
  docs.value = await api.listRagDocs(pid.value, kbId.value)
}

async function loadEval() {
  if (!kbId.value) {
    evalCases.value = []
    return
  }
  evalCases.value = await api.listRagEvalCases(pid.value, kbId.value)
}

async function onKbChange() {
  syncStrategyFromKb()
  await Promise.all([loadDocs(), loadEval()])
  evalResult.value = null
}

async function createKb() {
  const row = await api.createRagKb(pid.value, { ...kbForm })
  showKbDialog.value = false
  kbForm.name = ''
  kbForm.description = ''
  await loadKbs()
  kbId.value = row.id
  await onKbChange()
  ElMessage.success(t('rag.kbCreated'))
}

function onFile(f: any) {
  file.value = f.raw
  if (!title.value) title.value = f.name
  const reader = new FileReader()
  reader.onload = () => {
    content.value = String(reader.result || '')
  }
  reader.readAsText(f.raw)
}

async function doPreview() {
  const data = await api.previewRagChunks(pid.value, {
    content: content.value,
    chunk_strategy: strategy.value,
    chunk_size: chunkSize.value,
    chunk_overlap: chunkOverlap.value,
  })
  previewChunks.value = data.chunks || []
  tab.value = 'preview'
}

async function upload() {
  if (!kbId.value) return
  uploading.value = true
  try {
    const form = new FormData()
    form.append('title', title.value || 'doc')
    form.append('kb_id', kbId.value)
    form.append('chunk_strategy', strategy.value)
    form.append('chunk_size', String(chunkSize.value))
    form.append('chunk_overlap', String(chunkOverlap.value))
    if (file.value) form.append('file', file.value)
    else form.append('content', content.value)
    await api.uploadRag(pid.value, form)
    ElMessage.success(t('rag.indexed'))
    content.value = ''
    file.value = null
    await Promise.all([loadDocs(), loadKbs()])
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail?.message || e?.message || t('rag.indexFail'))
  } finally {
    uploading.value = false
  }
}

async function removeDoc(id: string) {
  await api.deleteRag(pid.value, id)
  await Promise.all([loadDocs(), loadKbs()])
}

async function openDoc(row: any) {
  drawerDoc.value = await api.getRagDoc(pid.value, row.id)
  docDrawer.value = true
}

async function reindex() {
  if (!kbId.value) return
  reindexing.value = true
  try {
    await api.reindexRagKb(pid.value, kbId.value)
    ElMessage.success(t('rag.reindexed'))
    await loadDocs()
  } finally {
    reindexing.value = false
  }
}

async function doSearch() {
  if (!searchQ.value.trim()) return
  searching.value = true
  searched.value = true
  try {
    const data = await api.searchRag(pid.value, { query: searchQ.value, kb_id: kbId.value || null, top_k: searchTopK.value })
    searchHits.value = data.hits || []
  } finally {
    searching.value = false
  }
}

async function addEvalCase() {
  if (!kbId.value || !evalQuery.value.trim()) return
  const keywords = evalKeywords.value
    .split(/[,，]/)
    .map((s) => s.trim())
    .filter(Boolean)
  await api.createRagEvalCase(pid.value, {
    kb_id: kbId.value,
    query: evalQuery.value,
    expected_keywords: keywords,
    expected_doc_ids: evalDocIds.value,
  })
  evalQuery.value = ''
  evalKeywords.value = ''
  evalDocIds.value = []
  await loadEval()
}

async function removeEval(id: string) {
  await api.deleteRagEvalCase(pid.value, id)
  await loadEval()
}

async function runEval() {
  if (!kbId.value) return
  evalRunning.value = true
  try {
    evalResult.value = await api.runRagEval(pid.value, { kb_id: kbId.value, top_k: searchTopK.value })
  } finally {
    evalRunning.value = false
  }
}

async function bootstrap() {
  kbId.value = ''
  await loadMeta()
  await loadKbs()
  await onKbChange()
}

watch(
  () => route.params.id,
  () => {
    void bootstrap()
  },
)

onMounted(() => {
  void bootstrap()
})
</script>

<style scoped>
.rag {
  display: grid;
  gap: 12px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  padding: 12px 14px;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-right: auto;
}
.pill {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--teal-soft);
  color: var(--teal-deep);
}
.pill.mute {
  background: rgba(18, 32, 43, 0.06);
  color: var(--mute);
}
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 980px) {
  .grid-2 {
    grid-template-columns: 1fr;
  }
}
.panel {
  padding: 14px 16px;
}
.panel h4 {
  margin: 0 0 10px;
}
.row {
  display: flex;
  gap: 10px;
  align-items: end;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.preview-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.chunks,
.hits {
  display: grid;
  gap: 10px;
  max-height: 640px;
  overflow: auto;
}
.chunk-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.75);
}
.chunk-card.hit {
  border-color: rgba(47, 157, 106, 0.45);
  background: rgba(47, 157, 106, 0.08);
}
.chunk-card.miss {
  border-color: rgba(200, 80, 80, 0.35);
  background: rgba(200, 80, 80, 0.06);
}
.chunk-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: var(--mute);
  margin-bottom: 6px;
}
.chunk-meta .sec {
  color: var(--teal-deep);
}
.chunk-card pre {
  margin: 0;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.45;
  font-family: var(--font-mono, ui-monospace, monospace);
}
.empty {
  color: var(--mute);
  padding: 24px;
  text-align: center;
}
.eval-summary {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}
.stat {
  display: grid;
  gap: 2px;
  padding: 10px 14px;
  border-radius: 12px;
  background: var(--teal-soft);
}
.stat b {
  font-size: 22px;
  color: var(--teal-deep);
}
.stat span {
  font-size: 12px;
  color: var(--mute);
}
.hit-list {
  display: grid;
  gap: 4px;
  font-size: 12px;
  color: var(--ink-soft);
}
.hit-line {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
