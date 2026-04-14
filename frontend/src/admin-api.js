import axios from 'axios'

const adminApi = axios.create({
  baseURL: '/api/admin',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const memoryAdminApi = {
  listUsers() {
    return adminApi.get('/memory/users')
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

export default adminApi
