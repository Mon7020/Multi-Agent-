<template>
  <section class="knowledge-admin-page">
    <article class="hero-card">
      <div>
        <p class="eyebrow">知识库管理</p>
        <h3>控制前台可见范围、发布状态与角色访问</h3>
        <p>后台可以按文件设置“前台可见 / 隐藏”，并管理草稿、已发布以及可访问角色范围。</p>
      </div>
      <button class="ghost-btn" @click="loadDocuments" :disabled="loading">
        {{ loading ? '刷新中…' : '刷新文件列表' }}
      </button>
    </article>

    <p v-if="successMessage" class="notice success">{{ successMessage }}</p>
    <p v-if="errorMessage" class="notice error">{{ errorMessage }}</p>
    <p v-if="isOperator" class="notice warning">当前角色为运营，只能查看知识文件状态，不能修改发布与显隐设置。</p>

    <div v-if="loading && documents.length === 0" class="empty-panel">正在加载知识文件…</div>

    <div v-else class="document-grid">
      <article v-for="doc in documents" :key="doc.document_id" class="document-card">
        <header class="document-head">
          <div>
            <h4>{{ doc.filename }}</h4>
            <p>{{ formatFileSize(doc.size) }} · {{ doc.file_type }} · {{ formatDate(doc.update_time) }}</p>
          </div>
          <div class="status-group">
            <span :class="['status-pill', draftState(doc)]">{{ doc.published ? '已发布' : '草稿' }}</span>
            <span :class="['status-pill', doc.visible_to_frontend ? 'visible' : 'hidden']">
              {{ doc.visible_to_frontend ? '前台显示' : '前台隐藏' }}
            </span>
          </div>
        </header>

        <div class="toggle-grid">
          <label class="switch-item">
            <span>前台可见</span>
            <input v-model="doc.visible_to_frontend" type="checkbox" :disabled="isOperator || savingDocId === doc.document_id" />
          </label>
          <label class="switch-item">
            <span>已发布</span>
            <input v-model="doc.published" type="checkbox" :disabled="isOperator || savingDocId === doc.document_id" />
          </label>
        </div>

        <div class="roles-block">
          <p class="roles-title">允许前台访问的角色</p>
          <div class="roles-grid">
            <label v-for="role in roleOptions" :key="role.value" class="role-chip">
              <input
                type="checkbox"
                :checked="doc.allowed_roles.includes(role.value)"
                :disabled="isOperator || savingDocId === doc.document_id"
                @change="toggleRole(doc, role.value, $event.target.checked)"
              />
              <span>{{ role.label }}</span>
            </label>
          </div>
        </div>

        <div class="actions-row">
          <button class="solid-btn" @click="saveDocument(doc)" :disabled="isOperator || savingDocId === doc.document_id">
            {{ savingDocId === doc.document_id ? '保存中…' : '保存设置' }}
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { knowledgeAdminApi } from '../../admin-api.js'
import { getAuthUser } from '../../auth/session.js'

const documents = ref([])
const loading = ref(false)
const savingDocId = ref('')
const errorMessage = ref('')
const successMessage = ref('')

const currentRole = computed(() => getAuthUser()?.role || '')
const isOperator = computed(() => currentRole.value === 'operator')

const roleOptions = [
  { value: 'user', label: '前台用户' },
  { value: 'operator', label: '运营' },
  { value: 'admin', label: '管理员' },
  { value: 'super_admin', label: '超级管理员' }
]

function setSuccess(message) {
  successMessage.value = message
  errorMessage.value = ''
}

function setError(message) {
  errorMessage.value = message
  successMessage.value = ''
}

async function loadDocuments() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await knowledgeAdminApi.listDocuments()
    documents.value = (response.data.documents || []).map((doc) => ({
      ...doc,
      allowed_roles: Array.isArray(doc.allowed_roles) ? [...doc.allowed_roles] : []
    }))
  } catch (error) {
    setError(error.response?.data?.detail || error.message || '加载知识文件失败')
  } finally {
    loading.value = false
  }
}

function toggleRole(doc, role, checked) {
  const next = new Set(doc.allowed_roles)
  if (checked) next.add(role)
  else next.delete(role)
  doc.allowed_roles = roleOptions.map((item) => item.value).filter((item) => next.has(item))
}

async function saveDocument(doc) {
  savingDocId.value = doc.document_id
  try {
    const response = await knowledgeAdminApi.updateDocument(doc.document_id, {
      visible_to_frontend: doc.visible_to_frontend,
      published: doc.published,
      allowed_roles: doc.allowed_roles
    })
    Object.assign(doc, response.data)
    setSuccess(`已更新 ${doc.filename} 的发布与可见范围`)
  } catch (error) {
    setError(error.response?.data?.detail || error.message || '保存知识文件设置失败')
  } finally {
    savingDocId.value = ''
  }
}

function formatDate(value) {
  if (!value) return '未知时间'
  return new Date(value).toLocaleString('zh-CN')
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function draftState(doc) {
  return doc.published ? 'published' : 'draft'
}

onMounted(() => {
  loadDocuments()
})
</script>

<style scoped>
.knowledge-admin-page {
  display: grid;
  gap: 18px;
}

.hero-card,
.document-card,
.empty-panel {
  background: rgba(255, 252, 247, 0.92);
  border: 1px solid rgba(33, 44, 66, 0.08);
  border-radius: 24px;
  box-shadow: 0 16px 40px rgba(33, 44, 66, 0.08);
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 24px;
}

.document-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.document-card {
  padding: 22px;
}

.document-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.document-head h4,
.hero-card h3 {
  font-family: Georgia, 'Times New Roman', serif;
}

.document-head p {
  margin-top: 8px;
  color: var(--text-secondary);
  line-height: 1.7;
}

.status-group,
.toggle-grid,
.roles-grid,
.actions-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.toggle-grid,
.roles-block,
.actions-row {
  margin-top: 18px;
}

.roles-grid {
  margin-top: 12px;
}

.roles-title,
.eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.status-pill,
.role-chip,
.switch-item {
  padding: 10px 12px;
  border-radius: 999px;
  background: rgba(246, 241, 233, 0.72);
  color: var(--text-secondary);
}

.status-pill.published {
  background: rgba(14, 97, 90, 0.12);
  color: var(--accent);
}

.status-pill.draft,
.status-pill.hidden {
  background: rgba(196, 111, 36, 0.14);
  color: #a65b1c;
}

.role-chip,
.switch-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.solid-btn,
.ghost-btn {
  padding: 12px 18px;
  border-radius: 999px;
}

.solid-btn {
  border: none;
  background: var(--accent);
  color: white;
}

.ghost-btn {
  border: 1px solid rgba(16, 98, 89, 0.18);
  background: rgba(255, 255, 255, 0.72);
}

.notice,
.empty-panel {
  padding: 16px 18px;
}

.notice.success {
  background: rgba(14, 97, 90, 0.1);
  color: var(--accent);
  border-radius: 16px;
}

.notice.error {
  background: rgba(180, 71, 55, 0.1);
  color: #9f3427;
  border-radius: 16px;
}

.notice.warning {
  background: rgba(196, 111, 36, 0.12);
  color: #8d5d26;
  border-radius: 16px;
}

@media (max-width: 960px) {
  .hero-card,
  .document-grid {
    grid-template-columns: 1fr;
  }

  .hero-card {
    flex-direction: column;
  }
}
</style>
