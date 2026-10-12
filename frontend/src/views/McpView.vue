<template>
  <div>
    <div class="page-head">
      <div>
        <h2 style="font-size: 22px">{{ t('mcp.title') }}</h2>
        <p>{{ t('mcp.tip') }}</p>
      </div>
      <el-button type="primary" @click="openCreate">{{ t('mcp.create') }}</el-button>
    </div>

    <div v-loading="loading" class="list">
      <article v-for="row in list" :key="row.id" class="card panel">
        <div class="top">
          <div>
            <h3>{{ row.name }}</h3>
            <div class="meta">
              <span class="status-pill">{{ row.transport }}</span>
              <code>{{ row.transport === 'stdio' ? row.command || '—' : row.url || '—' }}</code>
            </div>
          </div>
          <el-switch v-model="row.enabled" @change="toggle(row)" />
        </div>
        <p v-if="row.last_error" class="err">{{ row.last_error }}</p>
        <div class="tools" v-if="(row.tools_cache_json || []).length">
          <div class="block-title">{{ t('mcp.tools') }} ({{ row.tools_cache_json.length }})</div>
          <div v-for="tool in row.tools_cache_json" :key="tool.name" class="tool">
            <strong>{{ tool.name }}</strong>
            <span>{{ tool.description || '' }}</span>
          </div>
        </div>
        <div class="actions">
          <el-button link type="primary" :loading="probing === row.id" @click="probe(row)">{{ t('mcp.probe') }}</el-button>
          <el-button link type="primary" @click="openCall(row)">{{ t('mcp.call') }}</el-button>
          <el-button link type="primary" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
          <el-button link type="danger" @click="remove(row)">{{ t('common.delete') }}</el-button>
        </div>
      </article>
      <div v-if="!loading && !list.length" class="empty">{{ t('mcp.empty') }}</div>
    </div>

    <el-dialog
      v-model="dialog"
      :title="editing ? t('mcp.editTitle') : t('mcp.create')"
      width="560px"
      align-center
      destroy-on-close
      append-to-body
    >
      <el-form label-position="top">
        <el-form-item :label="t('common.name')" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item :label="t('mcp.transport')">
          <el-select v-model="form.transport" style="width: 100%">
            <el-option label="http" value="http" />
            <el-option label="sse" value="sse" />
            <el-option label="stdio" value="stdio" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.transport !== 'stdio'" :label="t('mcp.url')">
          <el-input v-model="form.url" placeholder="http://127.0.0.1:3100/mcp" />
        </el-form-item>
        <template v-else>
          <el-form-item :label="t('mcp.command')">
            <el-input v-model="form.command" placeholder="npx" />
          </el-form-item>
          <el-form-item :label="t('mcp.args')">
            <el-input v-model="argsText" :placeholder="t('mcp.argsPh')" />
          </el-form-item>
        </template>
        <el-form-item :label="t('mcp.headers')">
          <el-input v-model="headersText" type="textarea" :rows="3" :placeholder="t('mcp.headersPh')" />
        </el-form-item>
        <el-form-item :label="t('mcp.enabled')">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <p class="hint">{{ t('mcp.stdioHint') }}</p>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="dialog = false">{{ t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="callDialog"
      :title="t('mcp.callTitle')"
      width="520px"
      align-center
      destroy-on-close
      append-to-body
    >
      <el-form label-position="top">
        <el-form-item :label="t('mcp.toolName')">
          <el-select v-model="callForm.tool_name" filterable allow-create style="width: 100%">
            <el-option
              v-for="tool in callTarget?.tools_cache_json || []"
              :key="tool.name"
              :label="tool.name"
              :value="tool.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('mcp.arguments')">
          <el-input v-model="callArgsText" type="textarea" :rows="5" placeholder='{"key":"value"}' />
        </el-form-item>
        <pre v-if="callResult" class="result">{{ callResult }}</pre>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="callDialog = false">{{ t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="calling" @click="doCall">{{ t('mcp.call') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { inject, onMounted, reactive, ref, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const { t } = useI18n()
const project = inject<Ref<any>>('project')!
const list = ref<any[]>([])
const loading = ref(false)
const dialog = ref(false)
const saving = ref(false)
const probing = ref('')
const editing = ref<any>(null)
const form = reactive({
  name: '',
  transport: 'http',
  url: '',
  command: '',
  args_json: [] as string[],
  headers_json: {} as Record<string, string>,
  env_json: {} as Record<string, string>,
  enabled: true,
})
const argsText = ref('')
const headersText = ref('{}')

const callDialog = ref(false)
const callTarget = ref<any>(null)
const callForm = reactive({ tool_name: '' })
const callArgsText = ref('{}')
const callResult = ref('')
const calling = ref(false)

async function load() {
  loading.value = true
  try {
    list.value = await api.listMcpServers(project.value.id)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, {
    name: '',
    transport: 'http',
    url: '',
    command: '',
    args_json: [],
    headers_json: {},
    env_json: {},
    enabled: true,
  })
  argsText.value = ''
  headersText.value = '{}'
  dialog.value = true
}

function openEdit(row: any) {
  editing.value = row
  Object.assign(form, {
    name: row.name,
    transport: row.transport || 'http',
    url: row.url || '',
    command: row.command || '',
    args_json: row.args_json || [],
    headers_json: row.headers_json || {},
    env_json: row.env_json || {},
    enabled: !!row.enabled,
  })
  argsText.value = (row.args_json || []).join(' ')
  headersText.value = JSON.stringify(row.headers_json || {}, null, 2)
  dialog.value = true
}

function parseHeaders() {
  try {
    const obj = JSON.parse(headersText.value || '{}')
    if (obj && typeof obj === 'object' && !Array.isArray(obj)) return obj
  } catch {
    /* ignore */
  }
  throw new Error(t('mcp.badHeaders'))
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning(t('mcp.warnName'))
    return
  }
  let headers_json: Record<string, string>
  try {
    headers_json = parseHeaders()
  } catch (e: any) {
    ElMessage.error(e.message)
    return
  }
  const payload = {
    ...form,
    args_json: argsText.value.trim() ? argsText.value.trim().split(/\s+/) : [],
    headers_json,
  }
  saving.value = true
  try {
    if (editing.value) await api.updateMcpServer(project.value.id, editing.value.id, payload)
    else await api.createMcpServer(project.value.id, payload)
    dialog.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function toggle(row: any) {
  await api.updateMcpServer(project.value.id, row.id, {
    name: row.name,
    transport: row.transport,
    url: row.url || '',
    command: row.command || '',
    args_json: row.args_json || [],
    headers_json: row.headers_json || {},
    env_json: row.env_json || {},
    enabled: !!row.enabled,
  })
}

async function probe(row: any) {
  probing.value = row.id
  try {
    await api.probeMcpServer(project.value.id, row.id)
    ElMessage.success(t('mcp.probeOk'))
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail?.message || e.message || t('mcp.probeFail'))
    await load()
  } finally {
    probing.value = ''
  }
}

function openCall(row: any) {
  callTarget.value = row
  callForm.tool_name = row.tools_cache_json?.[0]?.name || ''
  callArgsText.value = '{}'
  callResult.value = ''
  callDialog.value = true
}

async function doCall() {
  if (!callTarget.value || !callForm.tool_name) return
  let argumentsObj: Record<string, any> = {}
  try {
    argumentsObj = JSON.parse(callArgsText.value || '{}')
  } catch {
    ElMessage.error(t('mcp.badArgs'))
    return
  }
  calling.value = true
  try {
    const res = await api.callMcpTool(project.value.id, callTarget.value.id, {
      tool_name: callForm.tool_name,
      arguments: argumentsObj,
    })
    callResult.value = JSON.stringify(res, null, 2)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail?.message || e.message || t('mcp.callFail'))
  } finally {
    calling.value = false
  }
}

async function remove(row: any) {
  await ElMessageBox.confirm(t('mcp.confirmDelete'), { type: 'warning' })
  await api.deleteMcpServer(project.value.id, row.id)
  await load()
}

onMounted(load)
</script>

<style scoped>
.list { display: grid; gap: 12px; min-height: 80px; }
.card { padding: 16px 18px; }
.top { display: flex; justify-content: space-between; gap: 16px; }
.top h3 { margin: 0; font-family: var(--font-brand); font-size: 18px; }
.meta { margin-top: 8px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.meta code { font-family: var(--font-mono); font-size: 12px; color: var(--ink-soft); }
.err { color: var(--danger, #c45c4a); font-size: 13px; }
.tools { margin-top: 12px; display: grid; gap: 6px; }
.block-title { font-size: 12px; color: var(--mute); letter-spacing: 0.06em; text-transform: uppercase; }
.tool { display: grid; gap: 2px; padding: 8px 10px; border-radius: 10px; background: rgba(15,143,134,0.05); border: 1px solid var(--line); font-size: 13px; }
.actions { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 4px; }
.empty { color: var(--mute); padding: 24px; text-align: center; }
.hint { color: var(--mute); font-size: 12px; margin: 0 0 4px; }
.result { margin: 0; padding: 10px; background: #0f172a0d; border-radius: 8px; max-height: 220px; overflow: auto; font-size: 12px; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 10px; }
</style>
