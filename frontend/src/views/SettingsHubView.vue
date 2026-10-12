<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>{{ t('settings.title') }}</h2>
        <p>{{ t('settings.subtitle') }}</p>
      </div>
    </div>

    <el-tabs v-model="tab" class="settings-tabs" @tab-change="onTab">
      <el-tab-pane :label="t('settings.tabProjects')" name="projects">
        <ProjectsView embedded />
      </el-tab-pane>
      <el-tab-pane :label="t('settings.tabEngines')" name="engines">
        <EnginesView embedded />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ProjectsView from './ProjectsView.vue'
import EnginesView from './EnginesView.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const tab = ref(String(route.query.tab || 'projects') === 'engines' ? 'engines' : 'projects')

function onTab(name: string | number) {
  router.replace({ path: '/settings', query: { tab: String(name) } })
}

watch(
  () => route.query.tab,
  (v) => {
    tab.value = String(v || 'projects') === 'engines' ? 'engines' : 'projects'
  },
)
</script>

<style scoped>
.settings-tabs {
  margin-top: 4px;
}
.settings-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}
.settings-tabs :deep(.el-tabs__item) {
  font-weight: 600;
}
</style>
