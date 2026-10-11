<template>
  <div class="panel form-wrap" v-if="project">
    <el-form label-position="top" class="form">
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="执行 Base URL">
        <el-input v-model="form.runtime_base_url" />
      </el-form-item>
      <el-form-item label="引擎 Profile">
        <el-select v-model="form.engine_profile_id" clearable style="width: 100%">
          <el-option v-for="e in engines" :key="e.id" :label="`${e.name} (${e.model})`" :value="e.id" />
        </el-select>
      </el-form-item>
      <el-button type="primary" @click="save">保存配置</el-button>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { inject, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const project = inject<any>('project')
const engines = ref<any[]>([])
const form = reactive({ description: '', runtime_base_url: '', engine_profile_id: '' as string | null })

watch(
  project,
  (p) => {
    if (!p) return
    const row = p.value || p
    if (!row?.id) return
    form.description = row.description || ''
    form.runtime_base_url = row.runtime_base_url || ''
    form.engine_profile_id = row.engine_profile_id || null
  },
  { immediate: true, deep: true },
)

onMounted(async () => {
  engines.value = await api.listEngines()
})

async function save() {
  const row = project?.value || project
  await api.updateProject(row.id, {
    name: row.name,
    description: form.description,
    runtime_base_url: form.runtime_base_url,
    runtime_headers: row.runtime_headers || {},
    engine_profile_id: form.engine_profile_id,
  })
  ElMessage.success('已保存')
  Object.assign(row, form)
}
</script>

<style scoped>
.form-wrap {
  padding: 20px 22px;
  max-width: 720px;
}
</style>
