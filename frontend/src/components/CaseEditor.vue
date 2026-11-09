<template>
  <el-drawer
    :model-value="modelValue"
    :title="t('caseEditor.title')"
    size="640px"
    destroy-on-close
    @close="emit('update:modelValue', false)"
  >
    <el-form v-if="form" label-position="top" class="form" v-loading="saving">
      <el-form-item :label="t('caseEditor.fields.title')" required>
        <el-input v-model="form.title" />
      </el-form-item>

      <div class="row-2">
        <el-form-item :label="t('caseEditor.fields.method')">
          <el-select v-model="form.method" style="width: 100%">
            <el-option v-for="m in methods" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('caseEditor.fields.priority')">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option label="P0" value="P0" />
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
          </el-select>
        </el-form-item>
      </div>

      <el-form-item :label="t('caseEditor.fields.path')">
        <el-input v-model="form.path" placeholder="/api/..." />
      </el-form-item>

      <el-form-item :label="t('caseEditor.fields.precondition')">
        <el-input v-model="form.precondition" type="textarea" :rows="2" />
      </el-form-item>

      <el-form-item :label="t('caseEditor.fields.steps')">
        <el-input v-model="stepsText" type="textarea" :rows="4" :placeholder="t('caseEditor.stepsPh')" />
      </el-form-item>

      <el-form-item :label="t('caseEditor.fields.expected')">
        <el-input v-model="form.expected" type="textarea" :rows="2" />
      </el-form-item>

      <el-form-item :label="t('caseEditor.fields.headers')">
        <el-input v-model="headersText" type="textarea" :rows="3" :placeholder='`{"Authorization":"Bearer {{token}}"}`' />
      </el-form-item>

      <el-form-item :label="t('caseEditor.fields.body')">
        <el-input v-model="bodyText" type="textarea" :rows="4" :placeholder="t('caseEditor.bodyPh')" />
      </el-form-item>

      <div class="section">{{ t('caseEditor.assertTitle') }}</div>
      <div class="row-2">
        <el-form-item :label="t('caseEditor.fields.statusCode')">
          <el-input-number v-model="form.status_code" :min="0" :max="599" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item :label="t('caseEditor.fields.maxMs')">
          <el-input-number v-model="form.max_ms" :min="0" :step="100" controls-position="right" style="width: 100%" />
        </el-form-item>
      </div>
      <el-form-item :label="t('caseEditor.fields.bodyContains')">
        <el-input v-model="bodyContainsText" :placeholder="t('caseEditor.bodyContainsPh')" />
      </el-form-item>

      <div class="list-head">
        <span>{{ t('caseEditor.fields.jsonpath') }}</span>
        <el-button link type="primary" @click="addJsonpath">{{ t('caseEditor.add') }}</el-button>
      </div>
      <div v-for="(jp, i) in form.jsonpath" :key="'jp' + i" class="kv-row">
        <el-input v-model="jp.path" placeholder="$.code" />
        <el-input v-model="jp.equalsText" :placeholder="t('caseEditor.equalsPh')" />
        <el-button link type="danger" @click="form.jsonpath.splice(i, 1)">{{ t('common.delete') }}</el-button>
      </div>

      <div class="list-head" style="margin-top: 14px">
        <span>{{ t('caseEditor.fields.extract') }}</span>
        <el-button link type="primary" @click="addExtract">{{ t('caseEditor.add') }}</el-button>
      </div>
      <div v-for="(ex, i) in form.extract" :key="'ex' + i" class="kv-row">
        <el-input v-model="ex.path" placeholder="$.data.token" />
        <el-input v-model="ex.as" placeholder="token" />
        <el-button link type="danger" @click="form.extract.splice(i, 1)">{{ t('common.delete') }}</el-button>
      </div>

      <div class="section">{{ t('caseEditor.mcpTitle') }}</div>
      <p class="hint">{{ t('caseEditor.mcpHint') }}</p>
      <div class="list-head">
        <span>{{ t('caseEditor.fields.mcpBefore') }}</span>
        <el-button link type="primary" @click="addMcp('before')">{{ t('caseEditor.add') }}</el-button>
      </div>
      <div v-for="(h, i) in form.mcp_before" :key="'mb' + i" class="mcp-row">
        <el-input v-model="h.server_name" :placeholder="t('caseEditor.serverPh')" />
        <el-input v-model="h.tool" :placeholder="t('caseEditor.toolPh')" />
        <el-input v-model="h.argsText" :placeholder='`{"id":"{{user_id}}"}`' />
        <el-input v-model="h.as" placeholder="as" style="max-width: 100px" />
        <el-button link type="danger" @click="form.mcp_before.splice(i, 1)">{{ t('common.delete') }}</el-button>
      </div>
      <div class="list-head" style="margin-top: 10px">
        <span>{{ t('caseEditor.fields.mcpAfter') }}</span>
        <el-button link type="primary" @click="addMcp('after')">{{ t('caseEditor.add') }}</el-button>
      </div>
      <div v-for="(h, i) in form.mcp_after" :key="'ma' + i" class="mcp-row">
        <el-input v-model="h.server_name" :placeholder="t('caseEditor.serverPh')" />
        <el-input v-model="h.tool" :placeholder="t('caseEditor.toolPh')" />
        <el-input v-model="h.argsText" :placeholder='`{"id":"{{user_id}}"}`' />
        <el-input v-model="h.as" placeholder="as" style="max-width: 100px" />
        <el-button link type="danger" @click="form.mcp_after.splice(i, 1)">{{ t('common.delete') }}</el-button>
      </div>

      <div class="footer">
        <el-button @click="emit('update:modelValue', false)">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</el-button>
      </div>
    </el-form>
  </el-drawer>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps<{ modelValue: boolean; caseRow: any | null }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'saved'): void }>()
const { t } = useI18n()

const methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
const saving = ref(false)
const stepsText = ref('')
const headersText = ref('{}')
const bodyText = ref('')
const bodyContainsText = ref('')

const form = reactive({
  title: '',
  method: 'GET',
  path: '/',
  priority: 'P1',
  precondition: '',
  expected: '',
  status_code: 200 as number | null,
  max_ms: null as number | null,
  jsonpath: [] as { path: string; equalsText: string }[],
  extract: [] as { path: string; as: string }[],
  mcp_before: [] as { server_name: string; tool: string; argsText: string; as: string }[],
  mcp_after: [] as { server_name: string; tool: string; argsText: string; as: string }[],
  tags: [] as string[],
})

function parseJsonLoose(raw: string, fallback: any) {
  const text = (raw || '').trim()
  if (!text) return fallback
  try {
    return JSON.parse(text)
  } catch {
    throw new Error(t('caseEditor.badJson'))
  }
}

function stringifyEquals(v: any) {
  if (typeof v === 'string') return v
  try {
    return JSON.stringify(v)
  } catch {
    return String(v)
  }
}

function parseEquals(raw: string) {
  const text = (raw || '').trim()
  if (!text) return ''
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function load(row: any) {
  const c = { ...(row?.content_json || {}) }
  form.title = row?.title || c.title || ''
  form.method = String(c.method || 'GET').toUpperCase()
  form.path = c.path || '/'
  form.priority = c.priority || 'P1'
  form.precondition = c.precondition || ''
  form.expected = c.expected || ''
  form.tags = Array.isArray(c.tags) ? c.tags : []
  stepsText.value = Array.isArray(c.steps) ? c.steps.join('\n') : String(c.steps || '')
  headersText.value = JSON.stringify(c.headers || {}, null, 2)
  bodyText.value =
    c.body == null || c.body === ''
      ? ''
      : typeof c.body === 'string'
        ? c.body
        : JSON.stringify(c.body, null, 2)
  const assert = c.assert || {}
  form.status_code = assert.status_code != null ? Number(assert.status_code) : 200
  form.max_ms = assert.max_ms != null ? Number(assert.max_ms) : null
  bodyContainsText.value = Array.isArray(assert.body_contains)
    ? assert.body_contains.join(', ')
    : assert.body_contains
      ? String(assert.body_contains)
      : ''
  const jp = assert.jsonpath || []
  if (Array.isArray(jp)) {
    form.jsonpath = jp.map((item: any) => ({
      path: String(item?.path || ''),
      equalsText: stringifyEquals(item?.equals ?? item?.value ?? ''),
    }))
  } else if (jp && typeof jp === 'object') {
    form.jsonpath = Object.entries(jp).map(([path, equals]) => ({
      path,
      equalsText: stringifyEquals(equals),
    }))
  } else {
    form.jsonpath = []
  }
  form.extract = Array.isArray(c.extract)
    ? c.extract.map((item: any) => ({
        path: String(item?.path || ''),
        as: String(item?.as || item?.name || ''),
      }))
    : []
  form.mcp_before = mapHooks(c.mcp_before)
  form.mcp_after = mapHooks(c.mcp_after)
}

function mapHooks(list: any) {
  if (!Array.isArray(list)) return []
  return list.map((item: any) => ({
    server_name: String(item?.server_name || item?.server_id || ''),
    tool: String(item?.tool || item?.name || ''),
    argsText:
      item?.arguments == null
        ? '{}'
        : typeof item.arguments === 'string'
          ? item.arguments
          : JSON.stringify(item.arguments),
    as: String(item?.as || item?.save_as || ''),
  }))
}

watch(
  () => [props.modelValue, props.caseRow] as const,
  ([open, row]) => {
    if (open && row) load(row)
  },
)

function addJsonpath() {
  form.jsonpath.push({ path: '', equalsText: '' })
}
function addExtract() {
  form.extract.push({ path: '', as: '' })
}
function addMcp(kind: 'before' | 'after') {
  const row = { server_name: '', tool: '', argsText: '{}', as: '' }
  if (kind === 'before') form.mcp_before.push(row)
  else form.mcp_after.push(row)
}

function parseHooks(list: { server_name: string; tool: string; argsText: string; as: string }[]) {
  return list
    .filter((h) => h.tool.trim())
    .map((h) => {
      let argumentsObj: any = {}
      try {
        argumentsObj = parseJsonLoose(h.argsText || '{}', {})
      } catch {
        argumentsObj = {}
      }
      const row: any = {
        server_name: h.server_name.trim() || undefined,
        tool: h.tool.trim(),
        arguments: argumentsObj,
      }
      if (h.as.trim()) row.as = h.as.trim()
      return row
    })
}

async function save() {
  if (!props.caseRow?.id) return
  if (!form.title.trim()) {
    ElMessage.warning(t('caseEditor.warnTitle'))
    return
  }
  saving.value = true
  try {
    const headers = parseJsonLoose(headersText.value, {})
    if (headers && typeof headers !== 'object') throw new Error(t('caseEditor.badJson'))
    let body: any = null
    const rawBody = bodyText.value.trim()
    if (rawBody) {
      try {
        body = JSON.parse(rawBody)
      } catch {
        body = rawBody
      }
    }
    const assert: Record<string, any> = {}
    if (form.status_code != null) assert.status_code = form.status_code
    if (form.max_ms != null && form.max_ms > 0) assert.max_ms = form.max_ms
    const contains = bodyContainsText.value
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    if (contains.length) assert.body_contains = contains
    const jsonpath = form.jsonpath
      .filter((j) => j.path.trim())
      .map((j) => ({ path: j.path.trim(), equals: parseEquals(j.equalsText) }))
    if (jsonpath.length) assert.jsonpath = jsonpath
    const extract = form.extract
      .filter((e) => e.path.trim() && e.as.trim())
      .map((e) => ({ path: e.path.trim(), as: e.as.trim() }))
    const mcp_before = parseHooks(form.mcp_before)
    const mcp_after = parseHooks(form.mcp_after)

    const content_json = {
      ...(props.caseRow.content_json || {}),
      title: form.title.trim(),
      method: form.method,
      path: form.path || '/',
      priority: form.priority,
      precondition: form.precondition,
      steps: stepsText.value
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean),
      expected: form.expected,
      headers,
      body,
      assert,
      extract,
      mcp_before,
      mcp_after,
      tags: form.tags.length ? form.tags : ['AI生成'],
    }
    delete content_json._confidence

    await api.patchTestCase(props.caseRow.id, {
      title: form.title.trim(),
      content_json,
    })
    ElMessage.success(t('caseEditor.saved'))
    emit('saved')
    emit('update:modelValue', false)
  } catch (e: any) {
    ElMessage.error(e.message || t('caseEditor.saveFail'))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.form {
  padding: 0 4px 24px;
}
.row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.section {
  margin: 8px 0 4px;
  font-family: var(--font-brand);
  font-weight: 650;
  color: var(--teal-deep);
}
.list-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--ink-soft);
  margin-bottom: 6px;
}
.kv-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}
.mcp-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1.2fr 90px auto;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}
.hint {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--mute);
}
.footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
@media (max-width: 700px) {
  .row-2,
  .kv-row {
    grid-template-columns: 1fr;
  }
}
</style>
