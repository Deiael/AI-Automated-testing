<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>{{ t('projects.title') }}</h2>
        <p>{{ t('projects.subtitle') }}</p>
      </div>
    </div>

    <section class="create panel">
      <div class="create-head">
        <div>
          <div class="kicker">New Project</div>
          <h3>{{ t('projects.createTitle') }}</h3>
        </div>
      </div>
      <el-form label-position="top" @submit.prevent>
        <div class="fields">
          <el-form-item :label="t('common.name')" required>
            <el-input v-model="form.name" :placeholder="t('projects.namePh')" />
          </el-form-item>
          <el-form-item :label="t('projects.baseUrl')">
            <el-input v-model="form.runtime_base_url" placeholder="https://httpbin.org" />
          </el-form-item>
          <el-form-item :label="t('common.description')" class="span-2">
            <el-input v-model="form.description" type="textarea" :rows="3" />
          </el-form-item>
        </div>
        <div class="actions">
          <el-button type="primary" size="large" :loading="creating" :disabled="!form.name.trim()" @click="create">
            {{ t('projects.createEnter') }}
          </el-button>
        </div>
      </el-form>
    </section>

    <div v-loading="loading" class="grid">
      <button
        v-for="row in list"
        :key="row.id"
        class="project-tile"
        @click="$router.push('/pipeline')"
      >
        <div class="tile-top">
          <span class="status-pill">{{ row.status || 'active' }}</span>
          <span class="mono id">{{ String(row.id).slice(0, 8) }}</span>
        </div>
        <h3>{{ row.name }}</h3>
        <p>{{ row.description || t('projects.noDesc') }}</p>
        <div class="tile-foot">
          <span>{{ row.runtime_base_url || t('projects.noBase') }}</span>
          <span class="enter" @click.stop="$router.push(`/projects/${row.id}/overview`)">{{ t('common.enter') }} →</span>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const { t } = useI18n()
const router = useRouter()
const list = ref<any[]>([])
const loading = ref(false)
const creating = ref(false)
const form = reactive({ name: '', description: '', runtime_base_url: 'https://httpbin.org' })

async function load() {
  loading.value = true
  try {
    list.value = await api.listProjects()
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!form.name.trim()) {
    ElMessage.warning(t('projects.warnName'))
    return
  }
  creating.value = true
  try {
    await api.createProject(form)
    router.push('/pipeline')
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.create { padding: 22px 24px; margin-bottom: 22px; }
.create-head { margin-bottom: 12px; }
.kicker { font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--teal-deep); font-weight: 650; }
.create-head h3 { margin: 4px 0 0; font-family: var(--font-brand); font-size: 20px; }
.fields { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 16px; }
.span-2 { grid-column: 1 / -1; }
.actions { display: flex; justify-content: flex-end; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; min-height: 80px; }
.project-tile { text-align: left; border: 1px solid var(--line); border-radius: 18px; padding: 18px; background: linear-gradient(160deg, rgba(255,255,255,0.92), rgba(247,250,251,0.75)); box-shadow: var(--shadow-soft); cursor: pointer; transition: transform 0.22s ease, border-color 0.22s ease; min-height: 190px; display: flex; flex-direction: column; font: inherit; color: inherit; }
.project-tile:hover { transform: translateY(-3px); border-color: rgba(15, 143, 134, 0.35); }
.tile-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.id { color: var(--mute); font-family: var(--font-mono); font-size: 12px; }
.project-tile h3 { margin: 0; font-family: var(--font-brand); font-size: 20px; }
.project-tile p { margin: 8px 0 0; color: var(--mute); font-size: 13px; line-height: 1.55; flex: 1; }
.tile-foot { margin-top: 16px; display: flex; justify-content: space-between; gap: 8px; font-size: 12px; color: var(--ink-soft); border-top: 1px solid var(--line); padding-top: 12px; }
.tile-foot span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%; font-family: var(--font-mono); }
.enter { color: var(--teal-deep); font-weight: 600; }
@media (max-width: 800px) { .fields { grid-template-columns: 1fr; } }
</style>
