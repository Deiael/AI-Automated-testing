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
  listEngines: () => http.get('/api/engine-profiles').then((r) => r.data),
  createEngine: (data: any) => http.post('/api/engine-profiles', data).then((r) => r.data),
  updateEngine: (id: string, data: any) => http.put(`/api/engine-profiles/${id}`, data).then((r) => r.data),
  engineHealth: (id: string) => http.get(`/api/engine-profiles/${id}/health`).then((r) => r.data),
  listRagDocs: (pid: string) => http.get(`/api/projects/${pid}/rag/docs`).then((r) => r.data),
  uploadRag: (pid: string, form: FormData) =>
    http.post(`/api/projects/${pid}/rag/docs`, form, { headers: { 'Content-Type': 'multipart/form-data' } }).then((r) => r.data),
  deleteRag: (pid: string, docId: string) => http.delete(`/api/projects/${pid}/rag/docs/${docId}`).then((r) => r.data),
  createSession: (data: any) => http.post('/api/sessions', data).then((r) => r.data),
  listMessages: (sid: string) => http.get(`/api/sessions/${sid}/messages`).then((r) => r.data),
  listTestPoints: (projectId: string) => http.get('/api/test-points', { params: { project_id: projectId } }).then((r) => r.data),
  patchTestPoint: (id: string, data: any) => http.patch(`/api/test-points/${id}`, data).then((r) => r.data),
  listTestCases: (projectId: string) => http.get('/api/test-cases', { params: { project_id: projectId } }).then((r) => r.data),
  patchTestCase: (id: string, data: any) => http.patch(`/api/test-cases/${id}`, data).then((r) => r.data),
  listRuns: (projectId: string) => http.get('/api/test-runs', { params: { project_id: projectId } }).then((r) => r.data),
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
}

export async function streamChat(
  sessionId: string,
  body: { message: string; engine_profile_id?: string; test_point_ids?: string[]; test_case_ids?: string[] },
  onEvent: (ev: { event: string; data: any }) => void,
) {
  const resp = await fetch(`/api/sessions/${sessionId}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': localStorage.getItem('apiKey') || 'dev-key',
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
