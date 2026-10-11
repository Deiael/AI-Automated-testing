<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>{{ t('engines.title') }}</h2>
        <p>{{ t('engines.subtitle') }}</p>
      </div>
      <el-button type="primary" size="large" @click="dialog = true">{{ t('engines.add') }}</el-button>
    </div>

    <div class="engine-grid">
      <article v-for="row in list" :key="row.id" class="engine-card panel">
        <div class="top">
          <h3>{{ row.name }}</h3>
          <span
            class="status-pill"
            :class="healthMap[row.id] ? (healthMap[row.id].ok ? '' : 'danger') : 'warn'"
          >
            {{
              healthMap[row.id]
                ? healthMap[row.id].ok
                  ? t('engines.healthy')
                  : t('engines.down')
                : t('engines.unknown')
            }}
          </span>
        </div>
        <div class="field">
          <span>{{ t('engines.url') }}</span>
          <code>{{ row.engine_base_url }}</code>
        </div>
        <div class="row2">
          <div class="field">
            <span>{{ t('engines.model') }}</span>
            <strong>{{ row.model }}</strong>
          </div>
          <div class="field">
            <span>{{ t('engines.vendor') }}</span>
            <strong>{{ row.vendor }}</strong>
          </div>
        </div>
        <el-button class="probe" @click="check(row.id)">{{ t('engines.probe') }}</el-button>
      </article>
    </div>

    <el-dialog v-model="dialog" :title="t('engines.dialogTitle')" width="520px">
      <el-form label-position="top">
        <el-form-item :label="t('common.name')"><el-input v-model="form.name" /></el-form-item>
        <el-form-item :label="t('engines.url')"><el-input v-model="form.engine_base_url" placeholder="http://127.0.0.1:8200" /></el-form-item>
        <el-form-item :label="t('engines.model')"><el-input v-model="form.model" /></el-form-item>
        <el-form-item :label="t('engines.vendor')"><el-input v-model="form.vendor" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="create">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'

const { t } = useI18n()
const list = ref<any[]>([])
const dialog = ref(false)
const healthMap = ref<Record<string, any>>({})
const form = reactive({
  name: 'engine-2',
  engine_base_url: 'http://127.0.0.1:8200',
  model: 'deepseek-chat',
  vendor: 'deepseek',
})

async function load() {
  list.value = await api.listEngines()
}

async function check(id: string) {
  healthMap.value[id] = await api.engineHealth(id)
}

async function create() {
  await api.createEngine({ ...form, extra_json: {} })
  dialog.value = false
  await load()
}

onMounted(load)
</script>

<style scoped>
.engine-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.engine-card { padding: 18px; display: flex; flex-direction: column; gap: 12px; }
.top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.engine-card h3 { margin: 0; font-family: var(--font-brand); font-size: 18px; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field span { font-size: 11px; color: var(--mute); letter-spacing: 0.08em; text-transform: uppercase; }
.field code, .field strong { font-size: 13px; }
.field code { font-family: var(--font-mono); word-break: break-all; }
.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.probe { margin-top: auto; align-self: flex-start; }
</style>
