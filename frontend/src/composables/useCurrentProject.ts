import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../api'

const STORAGE_KEY = 'currentProjectId'
const projects = ref<any[]>([])
const currentProjectId = ref<string>(localStorage.getItem(STORAGE_KEY) || '')
const loading = ref(false)

async function refreshProjects() {
  loading.value = true
  try {
    projects.value = await api.listProjects()
    if (currentProjectId.value && !projects.value.some((p) => p.id === currentProjectId.value)) {
      currentProjectId.value = projects.value[0]?.id || ''
    }
    if (!currentProjectId.value && projects.value[0]) {
      currentProjectId.value = projects.value[0].id
    }
    persist()
  } finally {
    loading.value = false
  }
}

function persist() {
  if (currentProjectId.value) localStorage.setItem(STORAGE_KEY, currentProjectId.value)
  else localStorage.removeItem(STORAGE_KEY)
}

function setCurrentProjectId(id: string) {
  currentProjectId.value = id
  persist()
}

const currentProject = computed(() => projects.value.find((p) => p.id === currentProjectId.value) || null)

export function useCurrentProject() {
  onMounted(() => {
    if (!projects.value.length) void refreshProjects()
  })
  watch(currentProjectId, persist)
  return {
    projects,
    currentProjectId,
    currentProject,
    loading,
    refreshProjects,
    setCurrentProjectId,
  }
}
