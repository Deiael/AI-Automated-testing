<template>
  <el-config-provider :locale="elLocale">
    <div class="shell">
      <aside class="rail">
        <div class="brand">
          <div class="mark" aria-hidden="true">
            <span></span><span></span><span></span>
          </div>
          <div>
            <div class="brand-name">{{ t('app.brand') }}</div>
            <div class="brand-sub">{{ t('app.brandSub') }}</div>
          </div>
        </div>

        <nav class="nav">
          <router-link class="nav-item" to="/pipeline" :class="{ active: isPipeline }">
            <span class="nav-ico">◎</span>
            <span>{{ t('nav.pipeline') }}</span>
          </router-link>
          <router-link class="nav-item" to="/settings" :class="{ active: isSettings }">
            <span class="nav-ico">⬡</span>
            <span>{{ t('nav.settings') }}</span>
          </router-link>
        </nav>

        <PetQuestPanel @adopt="adoptOpen = true" />
      </aside>

      <section class="main">
        <header class="topbar">
          <div class="crumb">
            <span class="crumb-kicker">{{ t('app.workbench') }}</span>
            <h1>{{ title }}</h1>
          </div>
          <div class="top-actions">
            <div class="project-switch">
              <span class="switch-label">{{ t('switcher.label') }}</span>
              <el-select
                :model-value="currentProjectId || undefined"
                filterable
                :placeholder="t('switcher.placeholder')"
                style="width: 180px"
                @change="onSwitchProject"
              >
                <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </div>
            <el-select
              class="lang-select"
              :model-value="locale"
              size="default"
              :aria-label="t('app.lang')"
              @change="switchLang"
            >
              <el-option :label="t('app.langZh')" value="zh-CN" />
              <el-option :label="t('app.langEn')" value="en-US" />
            </el-select>
            <label class="key-box">
              <span>{{ t('app.apiKey') }}</span>
              <input v-model="apiKey" @change="saveKey" spellcheck="false" />
            </label>
          </div>
        </header>
        <main class="content">
          <router-view />
        </main>
      </section>

      <PetBuddy />
      <PetPlayZone />
      <PetAdoptDialog v-model="adoptOpen" />
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'
import { setLocale, type AppLocale } from './i18n'
import { useCurrentProject } from './composables/useCurrentProject'
import { usePetStore } from './stores/pet'
import PetBuddy from './components/pet/PetBuddy.vue'
import PetPlayZone from './components/pet/PetPlayZone.vue'
import PetAdoptDialog from './components/pet/PetAdoptDialog.vue'
import PetQuestPanel from './components/pet/PetQuestPanel.vue'

const route = useRoute()
const { t, locale } = useI18n()
const { projects, currentProjectId, setCurrentProjectId, refreshProjects } = useCurrentProject()
const pet = usePetStore()

const isPipeline = computed(() => route.path.startsWith('/pipeline') || route.path.includes('/pipelines'))
const isSettings = computed(() => route.path.startsWith('/settings') || route.path.startsWith('/projects'))
const title = computed(() => {
  if (route.path.startsWith('/projects/') && route.params.id) return t('titles.projectDetail')
  if (isSettings.value) return t('titles.settings')
  return t('titles.pipeline')
})

watch(
  () => route.path,
  (path) => {
    if (path.startsWith('/settings') || path.startsWith('/projects')) {
      pet.completeQuest('open_settings')
    }
  },
  { immediate: true },
)

const elLocale = computed(() => (locale.value === 'en-US' ? en : zhCn))
const apiKey = ref(localStorage.getItem('apiKey') || 'dev-key')
const adoptOpen = ref(false)

function saveKey() {
  localStorage.setItem('apiKey', apiKey.value || 'dev-key')
}

function switchLang(lang: string) {
  setLocale(lang as AppLocale)
}

function onSwitchProject(id: string) {
  setCurrentProjectId(id)
}

onMounted(() => {
  void refreshProjects()
})
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 248px 1fr;
  min-height: 100%;
}

.rail {
  position: sticky;
  top: 0;
  height: 100vh;
  padding: 22px 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  border-right: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(247, 250, 251, 0.55));
  backdrop-filter: blur(16px);
  overflow: hidden;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 8px;
}

.mark {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(145deg, #128f87, #1d5f7a);
  display: grid;
  place-items: center;
  gap: 3px;
  box-shadow: 0 8px 20px rgba(15, 143, 134, 0.28);
}

.mark span {
  display: block;
  width: 16px;
  height: 2px;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 2px;
}

.mark span:nth-child(2) {
  width: 11px;
  opacity: 0.8;
}

.mark span:nth-child(3) {
  width: 7px;
  opacity: 0.55;
}

.brand-name {
  font-family: var(--font-brand);
  font-weight: 700;
  font-size: 18px;
  line-height: 1.1;
}

.brand-sub {
  font-size: 11px;
  color: var(--mute);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-top: 2px;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border-radius: 12px;
  color: var(--ink-soft);
  text-decoration: none;
  font-weight: 500;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.nav-item:hover {
  background: rgba(15, 143, 134, 0.08);
  color: var(--ink);
  transform: translateX(2px);
}

.nav-item.active {
  background: linear-gradient(90deg, rgba(15, 143, 134, 0.16), rgba(15, 143, 134, 0.05));
  color: var(--teal-deep);
  box-shadow: inset 3px 0 0 var(--teal);
}

.nav-ico {
  width: 18px;
  text-align: center;
  opacity: 0.8;
}

.main {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 28px 8px;
}

.crumb-kicker {
  display: inline-block;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--teal-deep);
  font-weight: 600;
}

.crumb h1 {
  margin: 4px 0 0;
  font-family: var(--font-brand);
  font-size: 26px;
  font-weight: 650;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.project-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 4px 4px 12px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.7);
}

.switch-label {
  font-size: 11px;
  color: var(--mute);
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.lang-select {
  width: 118px;
}

.lang-select :deep(.el-select__wrapper) {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  box-shadow: 0 0 0 1px var(--line) inset !important;
  min-height: 36px;
}

.lang-select :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--teal) inset !important;
}

.key-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.7);
}

.key-box span {
  font-size: 11px;
  color: var(--mute);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.key-box input {
  border: none;
  outline: none;
  background: transparent;
  width: 140px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--ink);
}

.content {
  padding: 8px 28px 32px;
  flex: 1;
}

@media (max-width: 1100px) {
  .project-switch .switch-label {
    display: none;
  }
}

@media (max-width: 900px) {
  .shell {
    grid-template-columns: 1fr;
  }
  .rail {
    position: relative;
    height: auto;
    border-right: none;
    border-bottom: 1px solid var(--line);
  }
  .content,
  .topbar {
    padding-left: 16px;
    padding-right: 16px;
  }
  .top-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
}

</style>
