<template>
  <div>
    <div class="page-head">
      <div>
        <h2 style="font-size: 22px">{{ t('templates.title') }}</h2>
        <p>{{ t('templates.tip') }}</p>
      </div>
      <el-button type="primary" @click="openCreate">{{ t('templates.create') }}</el-button>
    </div>

    <div class="panel table-wrap">
      <el-table :data="list">
        <el-table-column prop="name" :label="t('common.name')" width="160" />
        <el-table-column prop="prompt_hint" :label="t('templates.hint')" min-width="160" />
        <el-table-column :label="t('templates.fields')" min-width="220">
          <template #default="{ row }">
            <div class="chips">
              <span v-for="f in fieldNames(row)" :key="f" class="chip" :class="{ req: isRequired(row, f) }">
                {{ f }}{{ isRequired(row, f) ? '*' : '' }}
              </span>
              <span v-if="!fieldNames(row).length" class="mute">—</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('common.actions')" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-drawer v-model="drawer" :title="editing ? t('templates.editTitle') : t('templates.create')" size="560px">
      <el-form label-position="top">
        <el-form-item :label="t('common.name')" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item :label="t('templates.hint')">
          <el-input v-model="form.prompt_hint" type="textarea" :rows="2" />
        </el-form-item>

        <div class="fields-head">
          <strong>{{ t('templates.schemaEditor') }}</strong>
          <el-button link type="primary" @click="addField">{{ t('templates.addField') }}</el-button>
        </div>
        <div v-for="(f, i) in form.fields" :key="i" class="field-row">
          <el-input v-model="f.name" :placeholder="t('templates.fieldName')" />
          <el-select v-model="f.type" style="width: 120px">
            <el-option label="string" value="string" />
            <el-option label="array" value="array" />
            <el-option label="object" value="object" />
            <el-option label="number" value="number" />
            <el-option label="boolean" value="boolean" />
          </el-select>
          <el-checkbox v-model="f.required">{{ t('common.required') }}</el-checkbox>
          <el-button link type="danger" @click="form.fields.splice(i, 1)">{{ t('common.delete') }}</el-button>
        </div>
      </el-form>
      <div class="footer">
        <el-button @click="drawer = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</el-button>
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

const props = defineProps<{ projectId?: string }>()
const emit = defineEmits<{ (e: 'changed'): void }>()
const { t } = useI18n()
const route = useRoute()
const pid = computed(() => props.projectId || String(route.params.id || ''))
const list = ref<any[]>([])
const drawer = ref(false)
const editing = ref<any>(null)
const saving = ref(false)
const form = reactive({
  name: '',
  prompt_hint: '',
  fields: [] as { name: string; type: string; required: boolean }[],
})

function fieldNames(row: any) {
  const propsMap = row?.schema_json?.properties || {}
  return Object.keys(propsMap)
}
function isRequired(row: any, name: string) {
  return (row?.schema_json?.required || []).includes(name)
}

async function load() {
  if (!pid.value) return
  list.value = await api.listTemplates(pid.value)
}

function openCreate() {
  editing.value = null
  form.name = 'custom-v1'
  form.prompt_hint = t('templates.defaultHint')
  form.fields = [
    { name: 'title', type: 'string', required: true },
    { name: 'steps', type: 'array', required: true },
    { name: 'expected', type: 'string', required: true },
    { name: 'priority', type: 'string', required: true },
    { name: 'method', type: 'string', required: false },
    { name: 'path', type: 'string', required: false },
    { name: 'assert', type: 'object', required: false },
    { name: 'extract', type: 'array', required: false },
  ]
  drawer.value = true
}

function openEdit(row: any) {
  editing.value = row
  form.name = row.name
  form.prompt_hint = row.prompt_hint || ''
  const propsMap = row.schema_json?.properties || {}
  const required = new Set(row.schema_json?.required || [])
  form.fields = Object.keys(propsMap).map((name) => ({
    name,
    type: propsMap[name]?.type || 'string',
    required: required.has(name),
  }))
  if (!form.fields.length) openCreate()
  drawer.value = true
}

function addField() {
  form.fields.push({ name: '', type: 'string', required: false })
}

function toSchema() {
  const properties: Record<string, any> = {}
  const required: string[] = []
  for (const f of form.fields) {
    const name = f.name.trim()
    if (!name) continue
    properties[name] = { type: f.type }
    if (f.required) required.push(name)
  }
  return { required, properties }
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning(t('templates.warnName'))
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      prompt_hint: form.prompt_hint,
      schema_json: toSchema(),
    }
    if (editing.value?.id) {
      await api.updateTemplate(pid.value, editing.value.id, payload)
    } else {
      await api.createTemplate(pid.value, payload)
    }
    ElMessage.success(t('templates.saved'))
    drawer.value = false
    await load()
    emit('changed')
  } finally {
    saving.value = false
  }
}

onMounted(load)
watch(pid, load)
</script>

<style scoped>
.table-wrap {
  padding: 8px 12px 16px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(18, 32, 43, 0.06);
  font-family: var(--font-mono);
}
.chip.req {
  background: rgba(15, 143, 134, 0.14);
  color: var(--teal-deep);
  font-weight: 700;
}
.mute {
  color: var(--mute);
}
.fields-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 8px 0;
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 120px auto auto;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
@media (max-width: 700px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>
