<template>
  <div v-if="project" class="page">
    <div class="hero panel">
      <div>
        <div class="kicker">Project</div>
        <h2>{{ project.name }}</h2>
        <p>{{ project.description || t('project.heroTip') }}</p>
      </div>
      <div class="meta">
        <div class="meta-item">
          <span>{{ t('project.baseUrl') }}</span>
          <code>{{ project.runtime_base_url || '—' }}</code>
        </div>
        <router-link class="back" to="/settings?tab=projects">{{ t('project.back') }}</router-link>
      </div>
    </div>

    <div class="tabs">
      <router-link
        v-for="tab in tabs"
        :key="tab.to"
        :to="tab.to"
        class="tab"
        :class="{ active: isActive(tab.to) }"
      >
        {{ t(tab.labelKey) }}
      </router-link>
    </div>

    <div class="body">
      <router-view @refresh="load" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, provide, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { useCurrentProject } from '../composables/useCurrentProject'

const { t } = useI18n()
const route = useRoute()
const id = computed(() => String(route.params.id))
const project = ref<any>(null)
provide('project', project)
const { setCurrentProjectId } = useCurrentProject()

const tabs = computed(() => [
  { labelKey: 'project.tabs.overview', to: `/projects/${id.value}/overview` },
  { labelKey: 'project.tabs.rag', to: `/projects/${id.value}/rag` },
  { labelKey: 'project.tabs.skills', to: `/projects/${id.value}/skills` },
  { labelKey: 'project.tabs.mcp', to: `/projects/${id.value}/mcp` },
])

function isActive(to: string) {
  return route.path === to || route.path.startsWith(to + '/')
}

async function load() {
  project.value = await api.getProject(id.value)
  setCurrentProjectId(id.value)
}

onMounted(load)
watch(id, load)
</script>

<style scoped>
.hero {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 20px 22px;
  margin-bottom: 14px;
}

.kicker {
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--teal-deep);
  font-weight: 650;
}

.hero h2 {
  margin: 4px 0 0;
  font-family: var(--font-brand);
  font-size: 28px;
}

.hero p {
  margin: 8px 0 0;
  color: var(--mute);
  max-width: 560px;
  line-height: 1.55;
}

.meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-end;
  font-size: 12px;
  color: var(--mute);
}

.meta-item code {
  font-family: var(--font-mono);
  color: var(--ink-soft);
  font-size: 12px;
}

.back {
  color: var(--teal-deep);
  text-decoration: none;
  font-weight: 600;
  font-size: 13px;
}

.tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.tab {
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.7);
  color: var(--ink-soft);
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
}

.tab.active {
  color: var(--teal-deep);
  border-color: rgba(15, 143, 134, 0.35);
  background: var(--teal-soft);
}

.body {
  min-height: 320px;
}
</style>
