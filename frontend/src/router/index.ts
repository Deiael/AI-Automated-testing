import { createRouter, createWebHistory } from 'vue-router'
import ProjectsView from '../views/ProjectsView.vue'
import ProjectLayout from '../views/ProjectLayout.vue'
import OverviewView from '../views/OverviewView.vue'
import RagView from '../views/RagView.vue'
import TemplatesView from '../views/TemplatesView.vue'
import TestPointsView from '../views/TestPointsView.vue'
import TestCasesView from '../views/TestCasesView.vue'
import RunsView from '../views/RunsView.vue'
import EnginesView from '../views/EnginesView.vue'
import PipelineHubView from '../views/PipelineHubView.vue'
import PipelineView from '../views/PipelineView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/pipeline' },
    { path: '/pipeline', component: PipelineHubView },
    { path: '/pipelines/:pipelineId', component: PipelineView },
    { path: '/projects', component: ProjectsView },
    { path: '/settings/engines', component: EnginesView },
    {
      path: '/projects/:id',
      component: ProjectLayout,
      children: [
        { path: '', redirect: (to) => `/projects/${to.params.id}/overview` },
        { path: 'pipeline', redirect: '/pipeline' },
        { path: 'overview', component: OverviewView },
        { path: 'rag', component: RagView },
        { path: 'templates', component: TemplatesView },
        { path: 'testpoints', component: TestPointsView },
        { path: 'testcases', component: TestCasesView },
        { path: 'runs', component: RunsView },
      ],
    },
  ],
})

export default router
