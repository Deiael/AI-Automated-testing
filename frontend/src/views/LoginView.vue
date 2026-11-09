<template>
  <div class="login-page">
    <div class="card">
      <div class="brand">AI-Test</div>
      <p class="sub">{{ t('auth.subtitle') }}</p>
      <el-tabs v-model="mode">
        <el-tab-pane :label="t('auth.login')" name="login" />
        <el-tab-pane v-if="allowRegister" :label="t('auth.register')" name="register" />
      </el-tabs>
      <el-form label-position="top" @submit.prevent>
        <el-form-item :label="t('auth.username')">
          <el-input v-model="username" autocomplete="username" />
        </el-form-item>
        <el-form-item :label="t('auth.password')">
          <el-input v-model="password" type="password" show-password autocomplete="current-password" @keyup.enter="submit" />
        </el-form-item>
        <el-form-item v-if="mode === 'register'" :label="t('auth.email')">
          <el-input v-model="email" />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">
          {{ mode === 'login' ? t('auth.login') : t('auth.register') }}
        </el-button>
      </el-form>
      <p class="hint">{{ t('auth.apiKeyHint') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const { t } = useI18n()
const router = useRouter()
const mode = ref<'login' | 'register'>('login')
const allowRegister = ref(true)
const username = ref('')
const password = ref('')
const email = ref('')
const loading = ref(false)

async function submit() {
  if (!username.value.trim() || !password.value) {
    ElMessage.warning(t('auth.warnEmpty'))
    return
  }
  loading.value = true
  try {
    const res =
      mode.value === 'login'
        ? await api.login({ username: username.value.trim(), password: password.value })
        : await api.register({ username: username.value.trim(), password: password.value, email: email.value })
    localStorage.setItem('accessToken', res.access_token)
    localStorage.setItem('authUser', JSON.stringify(res.user))
    ElMessage.success(t('auth.ok'))
    router.replace('/pipeline')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || t('auth.fail'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(18, 143, 135, 0.18), transparent 60%),
    radial-gradient(900px 500px at 100% 0%, rgba(29, 95, 122, 0.16), transparent 55%),
    linear-gradient(180deg, #f7fafb, #eef3f5);
}
.card {
  width: min(420px, 100%);
  padding: 28px 26px 22px;
  border-radius: 18px;
  border: 1px solid rgba(15, 40, 50, 0.08);
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 20px 50px rgba(20, 40, 50, 0.08);
}
.brand {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.03em;
}
.sub {
  color: var(--muted);
  margin: 6px 0 12px;
}
.hint {
  margin-top: 14px;
  font-size: 12px;
  color: var(--muted);
}
</style>
