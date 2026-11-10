import { http } from './http'

export const api = {
  listProjects: () => http.get('/api/projects').then((r) => r.data),
  createProject: (data: any) => http.post('/api/projects', data).then((r) => r.data),
  getProject: (id: string) => http.get(`/api/projects/${id}`).then((r) => r.data),
  updateProject: (id: string, data: any) => http.put(`/api/projects/${id}`, data).then((r) => r.data),
  listPipelines: () => http.get('/api/pipelines').then((r) => r.data),
  createPipeline: (data: any) => http.post('/api/pipelines', data).then((r) => r.data),
  getPipeline: (id: string) => http.get(`/api/pipelines/${id}`).then((r) => r.data),
  patchPipeline: (id: string, data: any) => http.patch(`/api/pipelines/${id}`, data).then((r) => r.data),
  deletePipeline: (id: string) => http.delete(`/api/pipelines/${id}`).then((r) => r.data),
  listTemplates: (pid: string) => http.get(`/api/projects/${pid}/templates`).then((r) => r.data),
  createTemplate: (pid: string, data: any) => http.post(`/api/projects/${pid}/templates`, data).then((r) => r.data),
  updateTemplate: (pid: string, id: string, data: any) =>
    http.put(`/api/projects/${pid}/templates/${id}`, data).then((r) => r.data),
  listEngines: () => http.get('/api/engine-profiles').then((r) => r.data),
  createEngine: (data: any) => http.post('/api/engine-profiles', data).then((r) => r.data),
  updateEngine: (id: string, data: any) => http.put(`/api/engine-profiles/${id}`, data).then((r) => r.data),
  engineHealth: (id: string) => http.get(`/api/engine-profiles/${id}/health`).then((r) => r.data),
  listRagDocs: (pid: string, kbId?: string, pipelineId?: string) =>
    http
      .get(`/api/projects/${pid}/rag/docs`, {
        params: {
          ...(kbId ? { kb_id: kbId } : {}),
          ...(pipelineId ? { pipeline_id: pipelineId } : {}),
        },
      })
      .then((r) => r.data),
  getRagDoc: (pid: string, docId: string) => http.get(`/api/projects/${pid}/rag/docs/${docId}`).then((r) => r.data),
  uploadRag: (pid: string, form: FormData) =>
    http.post(`/api/projects/${pid}/rag/docs`, form, { headers: { 'Content-Type': 'multipart/form-data' } }).then((r) => r.data),
  deleteRag: (pid: string, docId: string) => http.delete(`/api/projects/${pid}/rag/docs/${docId}`).then((r) => r.data),
  ragMeta: (pid: string) => http.get(`/api/projects/${pid}/rag/meta`).then((r) => r.data),
  listRagKbs: (pid: string) => http.get(`/api/projects/${pid}/rag/knowledge-bases`).then((r) => r.data),
  createRagKb: (pid: string, data: any) => http.post(`/api/projects/${pid}/rag/knowledge-bases`, data).then((r) => r.data),
  updateRagKb: (pid: string, kbId: string, data: any) =>
    http.put(`/api/projects/${pid}/rag/knowledge-bases/${kbId}`, data).then((r) => r.data),
  deleteRagKb: (pid: string, kbId: string) => http.delete(`/api/projects/${pid}/rag/knowledge-bases/${kbId}`).then((r) => r.data),
  previewRagChunks: (pid: string, data: any) => http.post(`/api/projects/${pid}/rag/preview`, data).then((r) => r.data),
  searchRag: (pid: string, data: any) => http.post(`/api/projects/${pid}/rag/search`, data).then((r) => r.data),
  reindexRagKb: (pid: string, kbId: string) =>
    http.post(`/api/projects/${pid}/rag/knowledge-bases/${kbId}/reindex`).then((r) => r.data),
  listRagEvalCases: (pid: string, kbId: string) =>
    http.get(`/api/projects/${pid}/rag/eval-cases`, { params: { kb_id: kbId } }).then((r) => r.data),
  createRagEvalCase: (pid: string, data: any) => http.post(`/api/projects/${pid}/rag/eval-cases`, data).then((r) => r.data),
  deleteRagEvalCase: (pid: string, id: string) => http.delete(`/api/projects/${pid}/rag/eval-cases/${id}`).then((r) => r.data),
  runRagEval: (pid: string, data: any) => http.post(`/api/projects/${pid}/rag/eval/run`, data).then((r) => r.data),
  createSession: (data: any) => http.post('/api/sessions', data).then((r) => r.data),
  listMessages: (sid: string) => http.get(`/api/sessions/${sid}/messages`).then((r) => r.data),
  listTestPoints: (projectId: string, pipelineId?: string) =>
    http.get('/api/test-points', { params: { project_id: projectId, pipeline_id: pipelineId } }).then((r) => r.data),
  patchTestPoint: (id: string, data: any) => http.patch(`/api/test-points/${id}`, data).then((r) => r.data),
  listTestCases: (projectId: string, pipelineId?: string) =>
    http.get('/api/test-cases', { params: { project_id: projectId, pipeline_id: pipelineId } }).then((r) => r.data),
  patchTestCase: (id: string, data: any) => http.patch(`/api/test-cases/${id}`, data).then((r) => r.data),
  createTestCase: (data: any) => http.post('/api/test-cases', data).then((r) => r.data),
  deleteTestCase: (id: string) => http.delete(`/api/test-cases/${id}`).then((r) => r.data),
  exportCases: (projectId: string, pipelineId?: string, format: 'json' | 'postman' = 'json') =>
    http
      .get('/api/test-cases/export', { params: { project_id: projectId, pipeline_id: pipelineId, format } })
      .then((r) => r.data),
  listRuns: (projectId: string, pipelineId?: string) =>
    http.get('/api/test-runs', { params: { project_id: projectId, pipeline_id: pipelineId } }).then((r) => r.data),
  getDashboard: (params?: { project_id?: string; pipeline_id?: string }) =>
    http.get('/api/analytics/dashboard', { params }).then((r) => r.data),
  listTrackingEvents: (params?: { project_id?: string; pipeline_id?: string; event?: string }) =>
    http.get('/api/analytics/events', { params }).then((r) => r.data),
  listReports: (runId?: string) => http.get('/api/test-reports', { params: runId ? { run_id: runId } : {} }).then((r) => r.data),
  getReport: (id: string) => http.get(`/api/test-reports/${id}`).then((r) => r.data),
  listSkills: (pid: string) => http.get(`/api/projects/${pid}/skills`).then((r) => r.data),
  createSkill: (pid: string, data: any) => http.post(`/api/projects/${pid}/skills`, data).then((r) => r.data),
  updateSkill: (pid: string, id: string, data: any) => http.put(`/api/projects/${pid}/skills/${id}`, data).then((r) => r.data),
  deleteSkill: (pid: string, id: string) => http.delete(`/api/projects/${pid}/skills/${id}`).then((r) => r.data),
  listMcpServers: (pid: string) => http.get(`/api/projects/${pid}/mcp-servers`).then((r) => r.data),
  createMcpServer: (pid: string, data: any) => http.post(`/api/projects/${pid}/mcp-servers`, data).then((r) => r.data),
  updateMcpServer: (pid: string, id: string, data: any) => http.put(`/api/projects/${pid}/mcp-servers/${id}`, data).then((r) => r.data),
  deleteMcpServer: (pid: string, id: string) => http.delete(`/api/projects/${pid}/mcp-servers/${id}`).then((r) => r.data),
  probeMcpServer: (pid: string, id: string) => http.post(`/api/projects/${pid}/mcp-servers/${id}/probe`).then((r) => r.data),
  callMcpTool: (pid: string, id: string, data: any) =>
    http.post(`/api/projects/${pid}/mcp-servers/${id}/call`, data).then((r) => r.data),
  login: (data: { username: string; password: string }) => http.post('/api/auth/login', data).then((r) => r.data),
  register: (data: { username: string; password: string; email?: string }) =>
    http.post('/api/auth/register', data).then((r) => r.data),
  me: () => http.get('/api/auth/me').then((r) => r.data),
  listUsers: () => http.get('/api/auth/users').then((r) => r.data),
  importOpenApi: (form: FormData) =>
    http
      .post('/api/openapi/import', form, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 60000 })
      .then((r) => r.data),
  listApiSpecs: (projectId: string, pipelineId?: string) =>
    http.get(`/api/projects/${projectId}/api-specs`, { params: { pipeline_id: pipelineId } }).then((r) => r.data),
  deleteApiSpec: (id: string) => http.delete(`/api/api-specs/${id}`).then((r) => r.data),
  getCoverage: (projectId: string, pipelineId?: string) =>
    http.get('/api/coverage', { params: { project_id: projectId, pipeline_id: pipelineId } }).then((r) => r.data),
  ciRun: (data: { project_id: string; pipeline_id?: string; trigger?: string; case_ids?: string[] }) =>
    http.post('/api/ci/run', data, { timeout: 180000 }).then((r) => r.data),
  listSchedules: (projectId?: string, pipelineId?: string) =>
    http.get('/api/schedules', { params: { project_id: projectId, pipeline_id: pipelineId } }).then((r) => r.data),
  createSchedule: (data: any) => http.post('/api/schedules', data).then((r) => r.data),
  patchSchedule: (id: string, data: any) => http.patch(`/api/schedules/${id}`, data).then((r) => r.data),
  deleteSchedule: (id: string) => http.delete(`/api/schedules/${id}`).then((r) => r.data),
  runSchedule: (id: string) => http.post(`/api/schedules/${id}/run`, {}, { timeout: 180000 }).then((r) => r.data),
  getDefectConfig: (projectId: string) => http.get(`/api/projects/${projectId}/defect-config`).then((r) => r.data),
  putDefectConfig: (projectId: string, data: any) =>
    http.put(`/api/projects/${projectId}/defect-config`, data).then((r) => r.data),
  listDefects: (projectId: string, pipelineId?: string) =>
    http.get('/api/defects', { params: { project_id: projectId, pipeline_id: pipelineId } }).then((r) => r.data),
  listBaselines: (projectId: string, pipelineId?: string) =>
    http.get('/api/regression/baselines', { params: { project_id: projectId, pipeline_id: pipelineId } }).then((r) => r.data),
  createBaseline: (data: { project_id: string; pipeline_id?: string; name?: string; note?: string }) =>
    http.post('/api/regression/baselines', data).then((r) => r.data),
  deleteBaseline: (id: string) => http.delete(`/api/regression/baselines/${id}`).then((r) => r.data),
  regressionPlan: (data: { project_id: string; pipeline_id?: string; baseline_id: string }) =>
    http.post('/api/regression/plan', data).then((r) => r.data),
  regressionGenerate: (data: {
    project_id: string
    pipeline_id?: string
    baseline_id: string
    confirm?: boolean
    execute?: boolean
  }) => http.post('/api/regression/generate', data, { timeout: 180000 }).then((r) => r.data),
  listRembgModels: () => http.get('/api/tools/rembg/models').then((r) => r.data),
  removeBg: (file: File, model = 'u2netp', alphaMatting = false) => {
    const form = new FormData()
    form.append('file', file)
    form.append('model', model)
    form.append('alpha_matting', String(alphaMatting))
    return http
      .post('/api/tools/rembg', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
        timeout: 180000,
      })
      .then((r) => r.data as Blob)
  },
}

export async function streamChat(
  sessionId: string,
  body: {
    message: string
    engine_profile_id?: string
    test_point_ids?: string[]
    test_case_ids?: string[]
    env_id?: string
  },
  onEvent: (ev: { event: string; data: any }) => void,
) {
  const resp = await fetch(`/api/sessions/${sessionId}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': localStorage.getItem('apiKey') || 'dev-key',
      ...(localStorage.getItem('accessToken')
        ? { Authorization: `Bearer ${localStorage.getItem('accessToken')}` }
        : {}),
    },
    body: JSON.stringify(body),
  })
  if (!resp.ok || !resp.body) {
    throw new Error(`chat failed: ${resp.status}`)
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''

  const consume = (chunk: string, flush = false) => {
    buf += chunk
    const parts = buf.split('\n\n')
    if (flush) {
      buf = ''
    } else {
      buf = parts.pop() || ''
    }
    for (const part of parts) {
      const line = part.split('\n').find((l) => l.startsWith('data:'))
      if (!line) continue
      const raw = line.slice(5).trim()
      if (!raw) continue
      try {
        onEvent(JSON.parse(raw))
      } catch {
        /* ignore */
      }
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      consume(decoder.decode(), true)
      break
    }
    consume(decoder.decode(value, { stream: true }))
  }
}
