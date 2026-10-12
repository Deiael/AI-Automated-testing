import { createRouter, createWebHistory } from 'vue-router'
import ProjectLayout from '../views/ProjectLayout.vue'
import OverviewView from '../views/OverviewView.vue'
import RagView from '../views/RagView.vue'
import SkillsView from '../views/SkillsView.vue'
import McpView from '../views/McpView.vue'
import PipelineHubView from '../views/PipelineHubView.vue'
import PipelineView from '../views/PipelineView.vue'
import SettingsHubView from '../views/SettingsHubView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/pipeline' },
    { path: '/pipeline', component: PipelineHubView },
    { path: '/pipelines/:pipelineId', component: PipelineView },
    { path: '/settings', component: SettingsHubView },
    { path: '/projects', redirect: { path: '/settings', query: { tab: 'projects' } } },
    { path: '/settings/engines', redirect: { path: '/settings', query: { tab: 'engines' } } },
    {
      path: '/projects/:id',
      component: ProjectLayout,
      children: [
        { path: '', redirect: (to) => `/projects/${to.params.id}/overview` },
        { path: 'pipeline', redirect: '/pipeline' },
        { path: 'overview', component: OverviewView },
        { path: 'rag', component: RagView },
        { path: 'skills', component: SkillsView },
        { path: 'mcp', component: McpView },
        { path: 'templates', redirect: '/pipeline' },
        { path: 'testpoints', redirect: '/pipeline' },
        { path: 'testcases', redirect: '/pipeline' },
        { path: 'runs', redirect: '/pipeline' },
      ],
    },
  ],
})

export default router
