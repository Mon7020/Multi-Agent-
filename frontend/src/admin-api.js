import axios from 'axios'
import { getAuthToken } from './auth/session.js'

const adminApi = axios.create({
  baseURL: '/api/admin',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

adminApi.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const dashboardAdminApi = {
  getSummary() {
    return adminApi.get('/dashboard/summary')
  }
}

export const memoryAdminApi = {
  listUsers(params = {}) {
    return adminApi.get('/memory/users', { params })
  },

  getUser(userId) {
    return adminApi.get(`/memory/users/${encodeURIComponent(userId)}`)
  },

  updatePreference(userId, payload) {
    return adminApi.post(`/memory/users/${encodeURIComponent(userId)}/preferences`, payload)
  },

  clearContext(userId) {
    return adminApi.delete(`/memory/users/${encodeURIComponent(userId)}/context`)
  },

  clearAll(userId) {
    return adminApi.delete(`/memory/users/${encodeURIComponent(userId)}`)
  }
}

export const userAdminApi = {
  listUsers(params = {}) {
    return adminApi.get('/users', { params })
  },

  updateRole(userId, role) {
    return adminApi.patch(`/users/${encodeURIComponent(userId)}/role`, { role })
  }
}

export const knowledgeAdminApi = {
  listDocuments() {
    return adminApi.get('/knowledge/documents')
  },

  updateDocument(documentId, payload) {
    return adminApi.patch(`/knowledge/documents/${encodeURIComponent(documentId)}`, payload)
  }
}

export const settingsAdminApi = {
  getSummary() {
    return adminApi.get('/settings/summary')
  },

  updateRuntime(payload) {
    return adminApi.post('/settings/runtime', payload)
  }
}

export default adminApi
