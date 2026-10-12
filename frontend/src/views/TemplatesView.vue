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
        <el-table-column prop="name" :label="t('common.name')" width="180" />
        <el-table-column prop="prompt_hint" :label="t('templates.hint')" />
        <el-table-column label="schema" min-width="240">
          <template #default="{ row }">
            <code class="mono">{{ JSON.stringify(row.schema_json) }}</code>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'
import { api } from '../api'

const props = defineProps<{ projectId?: string }>()
const emit = defineEmits<{ (e: 'changed'): void }>()
const { t } = useI18n()
const route = useRoute()
const pid = computed(() => props.projectId || String(route.params.id || ''))
const list = ref<any[]>([])

async function load() {
  if (!pid.value) return
  list.value = await api.listTemplates(pid.value)
}

async function openCreate() {
  const { value } = await ElMessageBox.prompt(t('templates.namePrompt'), t('templates.create'), {
    inputValue: 'custom-v1',
  })
  await api.createTemplate(pid.value, {
    name: value,
    prompt_hint: t('templates.defaultHint'),
    schema_json: {
      required: ['title', 'steps', 'expected', 'priority'],
      properties: {
        title: { type: 'string' },
        steps: { type: 'array' },
        expected: { type: 'string' },
        priority: { type: 'string' },
      },
    },
  })
  await load()
  emit('changed')
}

onMounted(load)
watch(pid, load)
</script>

<style scoped>
.table-wrap {
  padding: 8px 12px 16px;
}
.mono {
  font-size: 12px;
  word-break: break-all;
}
</style>
