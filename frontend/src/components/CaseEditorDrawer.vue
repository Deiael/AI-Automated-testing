<template>
  <el-drawer :model-value="modelValue" :title="t('caseEdit.title')" size="560px" @close="close">
    <el-form v-if="form" label-position="top" class="edit-form">
      <el-form-item :label="t('caseEdit.name')" required>
        <el-input v-model="form.title" />
      </el-form-item>
      <div class="row2">
        <el-form-item :label="t('caseEdit.method')">
          <el-select v-model="form.method" style="width: 100%">
            <el-option v-for="m in methods" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('caseEdit.priority')">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option label="P0" value="P0" />
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
          </el-select>
        </el-form-item>
      </div>
      <el-form-item :label="t('caseEdit.path')">
        <el-input v-model="form.path" placeholder="/api/..." />
      </el-form-item>
      <el-form-item :label="t('caseEdit.precondition')">
        <el-input v-model="form.precondition" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item :label="t('caseEdit.steps')">
        <el-input v-model="form.stepsText" type="textarea" :rows="4" :placeholder="t('caseEdit.stepsPh')" />
      </el-form-item>
      <el-form-item :label="t('caseEdit.expected')">
        <el-input v-model="form.expected" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item :label="t('caseEdit.headers')">
        <el-input v-model="form.headersText" type="textarea" :rows="3" placeholder='{"Authorization":"Bearer {{token}}"}' />
      </el-form-item>
      <el-form-item :label="t('caseEdit.body')">
        <el-input v-model="form.bodyText" type="textarea" :rows="4" placeholder="{ }" />
      </el-form-item>
      <div class="row2">
        <el-form-item :label="t('caseEdit.statusCode')">
          <el-input v-model="form.statusCode" />
        </el-form-item>
        <el-form-item :label="t('caseEdit.maxMs')">
          <el-input v-model="form.maxMs" placeholder="3000" />
        </el-form-item>
      </div>
      <el-form-item :label="t('caseEdit.bodyContains')">
        <el-input v-model="form.bodyContains" :placeholder="t('caseEdit.bodyContainsPh')" />
      </el-form-item>
      <el-form-item :label="t('caseEdit.jsonpath')">
        <el-input v-model="form.jsonpathText" type="textarea" :rows="3" :placeholder="t('caseEdit.jsonpathPh')" />
      </el-form-item>
      <el-form-item :label="t('caseEdit.extract')">
        <el-input v-model="form.extractText" type="textarea" :rows="3" :placeholder="t('caseEdit.extractPh')" />
      </el-form-item>
      <div class="actions">
        <el-button @click="close">{{ t('common.cancel') }}</el-button>
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
const methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD']
const saving = ref(false)
const form = reactive<any>(emptyForm())

watch(
  () => [props.modelValue, props.caseRow],
  () => {
    if (props.modelValue && props.caseRow) hydrate(props.caseRow)
  },
)

function emptyForm() {
  return {
    title: '',
    method: 'GET',
    priority: 'P1',
    path: '/',
    precondition: '',
    stepsText: '',
    expected: '',
    headersText: '{}',
    bodyText: '',
    statusCode: '200',
    maxMs: '',
    bodyContains: '',
    jsonpathText: '',
    extractText: '',
  }
}

function hydrate(row: any) {
  const c = { ...(row.content_json || {}), ...row }
  Object.assign(form, emptyForm(), {
    title: row.title || c.title || '',
    method: (c.method || 'GET').toUpperCase(),
    priority: c.priority || 'P1',
    path: c.path || '/',
    precondition: c.precondition || '',
    stepsText: Array.isArray(c.steps) ? c.steps.join('\n') : String(c.steps || ''),
    expected: c.expected || '',
    headersText: stringify(c.headers || {}),
    bodyText: c.body == null || c.body === '' ? '' : stringify(c.body),
    statusCode: String(c.assert?.status_code ?? 200),
    maxMs: c.assert?.max_ms != null ? String(c.assert.max_ms) : '',
    bodyContains: Array.isArray(c.assert?.body_contains)
      ? c.assert.body_contains.join(', ')
      : String(c.assert?.body_contains || ''),
    jsonpathText: formatJsonpath(c.assert?.jsonpath),
    extractText: formatExtract(c.extract),
  })
}

function stringify(v: any) {
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return String(v)
  }
}

function parseJson(raw: string, fallback: any) {
  const text = raw.trim()
  if (!text) return fallback
  try {
    return JSON.parse(text)
  } catch {
    throw new Error(t('caseEdit.badJson'))
  }
}

function formatJsonpath(v: any) {
  if (!v) return ''
  if (Array.isArray(v)) {
    return v
      .map((item) => (item?.path ? `${item.path} = ${JSON.stringify(item.equals ?? item.value ?? null)}` : ''))
      .filter(Boolean)
      .join('\n')
  }
  if (typeof v === 'object') {
    return Object.entries(v)
      .map(([k, val]) => `${k} = ${JSON.stringify(val)}`)
      .join('\n')
  }
  return String(v)
}

function parseJsonpath(text: string) {
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      const idx = line.indexOf('=')
      if (idx < 0) return { path: line, equals: true }
      const path = line.slice(0, idx).trim()
      const raw = line.slice(idx + 1).trim()
      let equals: any = raw
      try {
        equals = JSON.parse(raw)
      } catch {
        equals = raw
      }
      return { path, equals }
    })
}

function formatExtract(v: any) {
  if (!Array.isArray(v)) return ''
  return v.map((item) => `${item.path} as ${item.as || item.name}`).join('\n')
}

function parseExtract(text: string) {
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      const m = line.match(/^(.*?)\s+as\s+(\S+)$/i)
      if (m) return { path: m[1].trim(), as: m[2].trim() }
      return { path: line, as: line.replace(/^\$\.?/, '').replace(/[^\w]+/g, '_') }
    })
}

function close() {
  emit('update:modelValue', false)
}

async function save() {
  if (!props.caseRow) return
  saving.value = true
  try {
    const headers = parseJson(form.headersText, {})
    const body = form.bodyText.trim() ? parseJson(form.bodyText, form.bodyText) : null
    const assert: any = {}
    if (form.statusCode !== '') assert.status_code = Number(form.statusCode)
    if (form.maxMs !== '') assert.max_ms = Number(form.maxMs)
    const contains = form.bodyContains
      .split(',')
      .map((s: string) => s.trim())
      .filter(Boolean)
    if (contains.length) assert.body_contains = contains
    const jsonpath = parseJsonpath(form.jsonpathText)
    if (jsonpath.length) assert.jsonpath = jsonpath
    const content = {
      ...(props.caseRow.content_json || {}),
      title: form.title,
      method: form.method,
      path: form.path,
      priority: form.priority,
      precondition: form.precondition,
      steps: form.stepsText.split('\n').map((s: string) => s.trim()).filter(Boolean),
      expected: form.expected,
      headers,
      body,
      assert,
      extract: parseExtract(form.extractText),
    }
    await api.patchTestCase(props.caseRow.id, { title: form.title, content_json: content })
    ElMessage.success(t('caseEdit.saved'))
    emit('saved')
    close()
  } catch (e: any) {
    ElMessage.error(e.message || t('caseEdit.saveFail'))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.edit-form {
  padding-right: 8px;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
