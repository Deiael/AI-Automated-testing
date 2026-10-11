<template>
  <div>
    <div class="page-head">
      <div>
        <h2 style="font-size: 22px">用例模板</h2>
        <p>生成时由网关注入引擎，不写在 Prompt 配置里。</p>
      </div>
      <el-button type="primary" @click="openCreate">新建模板</el-button>
    </div>
    <div class="panel table-wrap">
      <el-table :data="list">
        <el-table-column prop="name" label="名称" width="180" />
        <el-table-column prop="prompt_hint" label="提示" />
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
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { api } from '../api'

const route = useRoute()
const pid = String(route.params.id)
const list = ref<any[]>([])

async function load() {
  list.value = await api.listTemplates(pid)
}

async function openCreate() {
  const { value } = await ElMessageBox.prompt('模板名称', '新建模板', { inputValue: 'custom-v1' })
  await api.createTemplate(pid, {
    name: value,
    prompt_hint: '自定义接口用例模板',
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
}

onMounted(load)
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
