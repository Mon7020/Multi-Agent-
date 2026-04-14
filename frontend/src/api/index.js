import axios from 'axios'

const API_BASE = '/api/v1'
const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

function encodeDocId(docId) {
  return encodeURIComponent(String(docId))
}

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getAuthUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function setAuthSession(session) {
  localStorage.setItem(TOKEN_KEY, session.token)
  localStorage.setItem(
    USER_KEY,
    JSON.stringify({
      user_id: session.user_id,
      username: session.username,
      expires_at: session.expires_at
    })
  )
}

export function clearAuthSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

api.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const authApi = {
  register(username, password) {
    return api.post('/auth/register', { username, password })
  },

  login(username, password) {
    return api.post('/auth/login', { username, password })
  },

  me() {
    return api.get('/auth/me')
  },

  getMemoryProfile() {
    return api.get('/auth/memory')
  },

  resolveMemoryPreference(key, value, confidence = 1.0) {
    return api.post('/auth/memory/resolve', { key, value, confidence })
  }
}

export const chatApi = {
  sendMessage(sessionId, message, history = []) {
    const user = getAuthUser()
    return api.post('/chat', {
      session_id: sessionId,
      user_id: user?.user_id || null,
      message,
      history
    })
  },

  streamMessage(sessionId, message, history = []) {
    const token = getAuthToken()
    const user = getAuthUser()

    return fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({
        session_id: sessionId,
        user_id: user?.user_id || null,
        message,
        history
      })
    })
  },

  getHistory(sessionId) {
    return api.get(`/chat/history/${encodeURIComponent(sessionId)}`)
  },

  clearHistory(sessionId) {
    return api.delete(`/chat/history/${encodeURIComponent(sessionId)}`)
  }
}

export const skillsApi = {
  getSkills() {
    return api.get('/skills')
  },

  getSkill(skillName) {
    return api.get(`/skills/${encodeURIComponent(skillName)}`)
  },

  getStats() {
    return api.get('/skills/stats')
  }
}

export const healthApi = {
  check() {
    return api.get('/health')
  }
}

export const knowledgeBaseApi = {
  getDocuments() {
    return api.get('/knowledge-base')
  },

  getDocument(docId) {
    return api.get(`/knowledge-base/${encodeDocId(docId)}`)
  },

  uploadDocument(file, chunkSize = 400, chunkOverlap = 50) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('chunk_size', chunkSize)
    formData.append('chunk_overlap', chunkOverlap)
    return api.post('/knowledge-base/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  updateDocument(docId, content) {
    return api.put(`/knowledge-base/${encodeDocId(docId)}`, { content })
  },

  deleteDocument(docId) {
    return api.delete(`/knowledge-base/${encodeDocId(docId)}`)
  },

  getParams() {
    return api.get('/knowledge-base/params')
  },

  updateParams(params) {
    return api.post('/knowledge-base/params', params)
  },

  reloadKnowledgeBase() {
    return api.post('/knowledge-base/reload')
  },

  clearCache() {
    return api.post('/knowledge-base/clear-cache')
  }
}

export default api
