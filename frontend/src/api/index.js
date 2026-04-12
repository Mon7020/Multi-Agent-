import axios from 'axios'

const API_BASE = '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const chatApi = {
  sendMessage(sessionId, message, history = []) {
    return api.post('/chat', {
      session_id: sessionId,
      message: message,
      history: history
    })
  },

  streamMessage(sessionId, message, history = []) {
    return fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        message: message,
        history: history
      })
    })
  },

  getHistory(sessionId) {
    return api.get(`/chat/history/${sessionId}`)
  },

  clearHistory(sessionId) {
    return api.delete(`/chat/history/${sessionId}`)
  }
}

export const skillsApi = {
  getSkills() {
    return api.get('/skills')
  },

  getSkill(skillName) {
    return api.get(`/skills/${skillName}`)
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
  // 获取文档列表
  getDocuments() {
    return api.get('/knowledge-base')
  },

  // 获取单个文档内容
  getDocument(docId) {
    return api.get(`/knowledge-base/${docId}`)
  },

  // 上传文档
  uploadDocument(file, chunkSize = 400, chunkOverlap = 50) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('chunk_size', chunkSize)
    formData.append('chunk_overlap', chunkOverlap)
    return api.post('/knowledge-base/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // 更新文档
  updateDocument(docId, content) {
    return api.put(`/knowledge-base/${docId}`, { content })
  },

  // 删除文档
  deleteDocument(docId) {
    return api.delete(`/knowledge-base/${docId}`)
  },

  // 获取RAG参数
  getParams() {
    return api.get('/knowledge-base/params')
  },

  // 更新RAG参数
  updateParams(params) {
    return api.post('/knowledge-base/params', params)
  },

  // 重新加载知识库
  reloadKnowledgeBase() {
    return api.post('/knowledge-base/reload')
  },

  // 清除缓存
  clearCache() {
    return api.post('/knowledge-base/clear-cache')
  }
}

export default api
