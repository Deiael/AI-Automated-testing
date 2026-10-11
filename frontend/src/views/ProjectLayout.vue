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
        <router-link class="back" to="/projects">{{ t('project.back') }}</router-link>
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

const { t } = useI18n()
const route = useRoute()
const id = computed(() => String(route.params.id))
const project = ref<any>(null)
provide('project', project)

const tabs = computed(() => [
  { labelKey: 'project.tabs.overview', to: `/projects/${id.value}/overview` },
  { labelKey: 'project.tabs.rag', to: `/projects/${id.value}/rag` },
  { labelKey: 'project.tabs.templates', to: `/projects/${id.value}/templates` },
  { labelKey: 'project.tabs.testpoints', to: `/projects/${id.value}/testpoints` },
  { labelKey: 'project.tabs.testcases', to: `/projects/${id.value}/testcases` },
  { labelKey: 'project.tabs.runs', to: `/projects/${id.value}/runs` },
])

function isActive(to: string) {
  return route.path === to || route.path.startsWith(to + '/')
}

async function load() {
  project.value = await api.getProject(id.value)
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
  margin: 6px 0 0;
  font-size: 28px;
}

.hero p {
  margin: 8px 0 0;
  color: var(--mute);
}

.meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
  min-width: 220px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.meta-item span {
  font-size: 11px;
  color: var(--mute);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.meta-item code {
  font-family: var(--font-mono);
  font-size: 12px;
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.back {
  color: var(--teal-deep);
  text-decoration: none;
  font-weight: 600;
  font-size: 13px;
}

.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
  padding: 6px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid var(--line);
}

.tab {
  text-decoration: none;
  color: var(--ink-soft);
  padding: 8px 14px;
  border-radius: 10px;
  font-weight: 500;
  font-size: 13px;
  transition: background 0.2s ease, color 0.2s ease;
}

.tab:hover {
  background: rgba(15, 143, 134, 0.08);
  color: var(--ink);
}

.tab.active {
  background: var(--teal);
  color: #fff;
}

.body {
  min-height: 320px;
}

@media (max-width: 800px) {
  .hero {
    flex-direction: column;
  }
  .meta {
    align-items: flex-start;
  }
  .meta-item {
    align-items: flex-start;
  }
}
</style>
