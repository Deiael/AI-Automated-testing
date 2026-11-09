<template>
  <div class="accounts">
    <p class="tip">{{ t('auth.accountsTip') }}</p>
    <el-table :data="users" size="small" v-loading="loading">
      <el-table-column prop="username" :label="t('auth.username')" />
      <el-table-column prop="email" :label="t('auth.email')" />
      <el-table-column prop="role" :label="t('auth.role')" width="120" />
    </el-table>
    <p v-if="error" class="err">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'

const { t } = useI18n()
const users = ref<any[]>([])
const loading = ref(false)
const error = ref('')

onMounted(async () => {
  loading.value = true
  try {
    users.value = await api.listUsers()
  } catch (e: any) {
    error.value = e?.response?.data?.detail || t('auth.adminOnly')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.tip,
.err {
  color: var(--muted);
  font-size: 13px;
  margin: 0 0 12px;
}
.err {
  color: var(--danger, #c45656);
}
</style>
