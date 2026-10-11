<template>
  <div class="page-block">
    <div class="panel upload">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="title" placeholder="文档标题" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="content" type="textarea" :rows="6" placeholder="粘贴接口说明 / OpenAPI 片段" />
        </el-form-item>
        <div class="actions">
          <el-upload :auto-upload="false" :show-file-list="false" :on-change="onFile">
            <el-button>选择文件</el-button>
          </el-upload>
          <el-button type="primary" @click="upload">上传并索引</el-button>
        </div>
      </el-form>
    </div>

    <div class="panel table-wrap">
      <el-table :data="docs">
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="source" label="来源" />
        <el-table-column prop="chunk_count" label="分块" width="80" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="danger" @click="remove(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const route = useRoute()
const pid = String(route.params.id)
const docs = ref<any[]>([])
const title = ref('')
const content = ref('')
const file = ref<File | null>(null)

async function load() {
  docs.value = await api.listRagDocs(pid)
}

function onFile(f: any) {
  file.value = f.raw
  if (!title.value) title.value = f.name
}

async function upload() {
  const form = new FormData()
  form.append('title', title.value || 'doc')
  if (file.value) form.append('file', file.value)
  else form.append('content', content.value)
  await api.uploadRag(pid, form)
  ElMessage.success('已索引')
  content.value = ''
  file.value = null
  await load()
}

async function remove(id: string) {
  await api.deleteRag(pid, id)
  await load()
}

onMounted(load)
</script>

<style scoped>
.page-block {
  display: grid;
  gap: 14px;
}
.upload,
.table-wrap {
  padding: 16px 18px;
}
.actions {
  display: flex;
  gap: 8px;
}
</style>
