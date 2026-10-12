<template>
  <div>
    <div class="page-head">
      <div>
        <h2 style="font-size: 22px">{{ t('skills.title') }}</h2>
        <p>{{ t('skills.tip') }}</p>
      </div>
      <el-button type="primary" @click="openCreate">{{ t('skills.create') }}</el-button>
    </div>

    <div v-loading="loading" class="list">
      <article v-for="row in list" :key="row.id" class="card panel">
        <div class="top">
          <div>
            <h3>{{ row.name }}</h3>
            <p>{{ row.description || t('skills.noDesc') }}</p>
          </div>
          <el-switch v-model="row.enabled" @change="toggle(row)" />
        </div>
        <pre class="content">{{ row.content || '—' }}</pre>
        <div class="actions">
          <el-button link type="primary" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
          <el-button link type="danger" @click="remove(row)">{{ t('common.delete') }}</el-button>
        </div>
      </article>
      <div v-if="!loading && !list.length" class="empty">{{ t('skills.empty') }}</div>
    </div>

    <el-dialog
      v-model="dialog"
      :title="editing ? t('skills.editTitle') : t('skills.create')"
      width="560px"
      align-center
      destroy-on-close
      append-to-body
    >
      <el-form label-position="top" class="skill-form">
        <el-form-item :label="t('common.name')" required>
          <el-input v-model="form.name" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item :label="t('common.description')">
          <el-input v-model="form.description" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item :label="t('skills.content')" required>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="6"
            resize="vertical"
            :placeholder="t('skills.contentPh')"
          />
        </el-form-item>
        <el-form-item :label="t('skills.enabled')" class="enabled-row">
          <div class="enabled-line">
            <el-switch v-model="form.enabled" />
            <span class="enabled-tip">{{ form.enabled ? t('skills.enabledOn') : t('skills.enabledOff') }}</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="dialog = false">{{ t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</el-button>
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
const editing = ref<any>(null)
const form = reactive({ name: '', description: '', content: '', enabled: true })

async function load() {
  loading.value = true
  try {
    list.value = await api.listSkills(project.value.id)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', description: '', content: '', enabled: true })
  dialog.value = true
}

function openEdit(row: any) {
  editing.value = row
  Object.assign(form, {
    name: row.name,
    description: row.description || '',
    content: row.content || '',
    enabled: !!row.enabled,
  })
  dialog.value = true
}

async function save() {
  if (!form.name.trim() || !form.content.trim()) {
    ElMessage.warning(t('skills.warnRequired'))
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await api.updateSkill(project.value.id, editing.value.id, { ...form })
    } else {
      await api.createSkill(project.value.id, { ...form })
    }
    dialog.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function toggle(row: any) {
  await api.updateSkill(project.value.id, row.id, {
    name: row.name,
    description: row.description || '',
    content: row.content || '',
    enabled: !!row.enabled,
  })
}

async function remove(row: any) {
  await ElMessageBox.confirm(t('skills.confirmDelete'), { type: 'warning' })
  await api.deleteSkill(project.value.id, row.id)
  await load()
}

onMounted(load)
</script>

<style scoped>
.list { display: grid; gap: 12px; min-height: 80px; }
.card { padding: 16px 18px; }
.top { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.top h3 { margin: 0; font-family: var(--font-brand); font-size: 18px; }
.top p { margin: 6px 0 0; color: var(--mute); font-size: 13px; }
.content {
  margin: 12px 0 0;
  padding: 12px;
  border-radius: 10px;
  background: rgba(15, 143, 134, 0.05);
  border: 1px solid var(--line);
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.55;
  max-height: 180px;
  overflow: auto;
}
.actions { margin-top: 10px; display: flex; gap: 8px; }
.empty { color: var(--mute); padding: 24px; text-align: center; }
.skill-form :deep(.el-form-item:last-child) { margin-bottom: 4px; }
.enabled-line { display: flex; align-items: center; gap: 10px; }
.enabled-tip { font-size: 13px; color: var(--mute); }
.dialog-actions { display: flex; justify-content: flex-end; gap: 10px; }
</style>
