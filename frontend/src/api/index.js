import axios from 'axios'

const API_BASE = '/api/v1'

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

export const chatApi = {
  sendMessage(sessionId, userId, message, history = []) {
    return api.post('/chat', {
      session_id: sessionId,
      user_id: userId,
      message,
      history
    })
  },

  streamMessage(sessionId, userId, message, history = []) {
    return fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        user_id: userId,
        message,
        history
      })
    })
  },

  getHistory(sessionId, userId) {
    return api.get(`/chat/history/${encodeURIComponent(sessionId)}`, {
      params: { user_id: userId }
    })
  },

  clearHistory(sessionId, userId) {
    return api.delete(`/chat/history/${encodeURIComponent(sessionId)}`, {
      params: { user_id: userId }
    })
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
