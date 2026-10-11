import axios from 'axios'

const API_KEY = localStorage.getItem('apiKey') || 'dev-key'

export const http = axios.create({
  baseURL: '/',
  headers: { 'X-API-Key': API_KEY },
})

http.interceptors.request.use((config) => {
  config.headers['X-API-Key'] = localStorage.getItem('apiKey') || 'dev-key'
  return config
})
