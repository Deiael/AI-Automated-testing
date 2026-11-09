import axios from 'axios'

const API_KEY = localStorage.getItem('apiKey') || 'dev-key'

export const http = axios.create({
  baseURL: '/',
  headers: { 'X-API-Key': API_KEY },
  timeout: 30000,
})

http.interceptors.request.use((config) => {
  config.headers['X-API-Key'] = localStorage.getItem('apiKey') || 'dev-key'
  const token = localStorage.getItem('accessToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      const path = window.location.pathname || ''
      if (!path.startsWith('/login') && localStorage.getItem('accessToken')) {
        // token invalid — clear and let user re-login (API key still works if present)
        localStorage.removeItem('accessToken')
        localStorage.removeItem('authUser')
      }
    }
    return Promise.reject(err)
  },
)
