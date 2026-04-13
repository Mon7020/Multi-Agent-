<template>
  <div class="kb-panel">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="upload-wrapper">
        <input type="file" accept=".txt,.pdf,.docx" @change="handleFileSelect" :disabled="uploading" />
        <span class="upload-label">{{ uploading ? '上传中...' : '上传文档' }}</span>
      </div>
      <button class="btn-secondary" @click="reloadKnowledgeBase" :disabled="loading">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M23 4v6h-6"/><path d="M1 20v-6h6"/>
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
        </svg>
        重载知识库
      </button>
      <button class="btn-secondary" @click="clearCache">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
        </svg>
        清理缓存
      </button>
    </div>

    <!-- 上传结果 -->
    <div v-if="uploadResult" :class="['toast', uploadResult.success ? 'success' : 'error']">
      {{ uploadResult.message }}
    </div>

    <!-- 统计栏 -->
    <div class="stats-bar">
      <div class="stat-item">
        <span class="stat-label">缓存类型</span>
        <span class="stat-value">{{ stats.cache_type || 'N/A' }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">缓存条目</span>
        <span class="stat-value">{{ stats.cache_keys || 0 }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">请求数</span>
        <span class="stat-value">{{ stats.total_requests || 0 }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">成功率</span>
        <span class="stat-value" :class="getRateClass(stats.success_rate)">{{ stats.success_rate || '0%' }}</span>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="layout">
      <!-- 文档列表 -->
      <div class="list-panel">
        <div class="panel-header">
          <h3>文档列表</h3>
          <span class="count-badge">{{ documents.length }}</span>
        </div>
        <div v-if="loading && documents.length === 0" class="empty-state">
          <div class="spinner"></div>
          <span>加载中...</span>
        </div>
        <div v-else-if="documents.length === 0" class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          <span>暂无文档</span>
        </div>
        <div v-else class="doc-list">
          <div
            v-for="doc in documents"
            :key="doc.id"
            :class="['doc-item', { selected: selectedDoc?.id === doc.id }]"
            @click="selectDocument(doc)"
          >
            <div class="doc-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
            </div>
            <div class="doc-main">
              <div class="doc-name">{{ doc.filename }}</div>
              <div class="doc-meta">
                <span>{{ formatFileSize(doc.size) }}</span>
                <span class="divider">|</span>
                <span>{{ doc.chunk_count }} chunks</span>
                <span class="divider">|</span>
                <span>{{ formatDate(doc.update_time) }}</span>
              </div>
            </div>
            <div class="doc-actions">
              <button class="icon-btn" @click.stop="editDocument(doc)" title="编辑">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
              <button class="icon-btn danger" @click.stop="deleteDocument(doc)" title="删除">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 文档编辑器 -->
      <div class="editor-panel" v-if="selectedDoc">
        <div class="panel-header">
          <div class="editor-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <span>{{ selectedDoc.filename }}</span>
          </div>
          <div class="editor-actions">
            <template v-if="!editing">
              <button class="btn-primary" @click="editDocument(selectedDoc)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
                编辑
              </button>
            </template>
            <template v-else>
              <button class="btn-primary" @click="saveDocument" :disabled="saving">
                {{ saving ? '保存中...' : '保存' }}
              </button>
              <button class="btn-secondary" @click="cancelEdit">取消</button>
            </template>
            <button class="btn-secondary" @click="closeEditor">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
              关闭
            </button>
          </div>
        </div>

        <textarea
          v-if="editing"
          v-model="editContent"
          class="editor-textarea"
          placeholder="仅支持 txt 文档在线编辑"
        ></textarea>
        <div v-else class="preview" v-html="formatContent(contentPreview)"></div>
      </div>

      <!-- 空状态编辑器 -->
      <div class="editor-panel empty" v-else>
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          <span>选择文档查看详情</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { knowledgeBaseApi } from '../api/index.js'

const documents = ref([])
const selectedDoc = ref(null)
const contentPreview = ref('')
const editContent = ref('')
const editing = ref(false)
const loading = ref(false)
const uploading = ref(false)
const uploadResult = ref(null)
const saving = ref(false)
const stats = ref({})

async function loadDocuments() {
  loading.value = true
  try {
    const res = await knowledgeBaseApi.getDocuments()
    documents.value = res.data.documents || []
  } catch (e) {
    console.error('load documents failed:', e)
  }
  loading.value = false
}

async function loadStats() {
  try {
    const res = await knowledgeBaseApi.getParams()
    stats.value = {
      cache_type: res.data.cache_stats?.type || 'N/A',
      cache_keys: res.data.cache_stats?.size || 0,
      total_requests: res.data.metrics?.total_requests || 0,
      success_rate: res.data.metrics?.success_rate || '0%'
    }
  } catch (e) {
    console.error('load stats failed:', e)
  }
}

async function selectDocument(doc) {
  selectedDoc.value = doc
  editing.value = false

  try {
    const res = await knowledgeBaseApi.getDocument(doc.id)
    contentPreview.value = res.data.content || ''
  } catch (e) {
    console.error('load document content failed:', e)
    contentPreview.value = '加载失败'
  }
}

function editDocument(doc) {
  selectedDoc.value = doc
  editing.value = true
  editContent.value = contentPreview.value
}

function cancelEdit() {
  editing.value = false
}

async function saveDocument() {
  if (!selectedDoc.value) return
  saving.value = true

  try {
    await knowledgeBaseApi.updateDocument(selectedDoc.value.id, editContent.value)
    editing.value = false
    await loadDocuments()
    await loadStats()
    await selectDocument(selectedDoc.value)
  } catch (e) {
    console.error('save document failed:', e)
    alert(e.response?.data?.detail || '保存失败')
  }

  saving.value = false
}

async function deleteDocument(doc) {
  if (!confirm(`确定删除文档 ${doc.filename} 吗？`)) return

  try {
    await knowledgeBaseApi.deleteDocument(doc.id)
    if (selectedDoc.value?.id === doc.id) {
      closeEditor()
    }
    await loadDocuments()
    await loadStats()
  } catch (e) {
    console.error('delete document failed:', e)
    alert('删除失败')
  }
}

async function handleFileSelect(event) {
  const file = event.target.files?.[0]
  if (!file) return

  uploading.value = true
  uploadResult.value = null

  try {
    const res = await knowledgeBaseApi.uploadDocument(file)
    uploadResult.value = {
      success: true,
      message: `上传成功：${file.name} (${res.data.chunk_count || 0} chunks)`
    }
    await loadDocuments()
    await loadStats()
  } catch (e) {
    uploadResult.value = {
      success: false,
      message: e.response?.data?.detail || e.message || '上传失败'
    }
  }

  uploading.value = false
  event.target.value = ''
}

async function reloadKnowledgeBase() {
  loading.value = true
  try {
    await knowledgeBaseApi.reloadKnowledgeBase()
    await loadDocuments()
    await loadStats()
    alert('知识库已重载')
  } catch (e) {
    alert(e.response?.data?.detail || '重载失败')
  }
  loading.value = false
}

async function clearCache() {
  try {
    await knowledgeBaseApi.clearCache()
    await loadStats()
    alert('缓存已清理')
  } catch (e) {
    alert(e.response?.data?.detail || '清理失败')
  }
}

function closeEditor() {
  selectedDoc.value = null
  editing.value = false
  contentPreview.value = ''
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function formatContent(content) {
  if (!content) return ''
  return escapeHtml(content).replace(/\n/g, '<br>')
}

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function getRateClass(value) {
  if (!value) return ''
  const parsed = typeof value === 'string' ? parseFloat(value) : Number(value)
  if (Number.isNaN(parsed)) return ''
  if (parsed >= 80 || parsed >= 0.8) return 'success'
  if (parsed >= 50 || parsed >= 0.5) return 'warning'
  return 'error'
}

onMounted(() => {
  loadDocuments()
  loadStats()
})
</script>

<style scoped>
.kb-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 工具栏 */
.toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.upload-wrapper {
  position: relative;
  display: inline-flex;
}

.upload-wrapper input[type="file"] {
  position: absolute;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.upload-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--accent);
  color: white;
  border-radius: var(--radius);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition);
}

.upload-label:hover {
  background: var(--accent-hover);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid var(--border);
  background: var(--surface);
  border-radius: var(--radius);
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition);
}

.btn-secondary:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-light);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary svg {
  width: 14px;
  height: 14px;
}

/* Toast */
.toast {
  padding: 10px 16px;
  border-radius: var(--radius);
  font-size: 13px;
  animation: slideIn 0.3s ease;
}

.toast.success {
  background: #ECFDF5;
  color: var(--success);
  border: 1px solid #A7F3D0;
}

.toast.error {
  background: #FEF2F2;
  color: var(--error);
  border: 1px solid #FECACA;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 统计栏 */
.stats-bar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  min-width: 100px;
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-value.success { color: var(--success); }
.stat-value.warning { color: var(--warning); }
.stat-value.error { color: var(--error); }

/* 主布局 */
.layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.list-panel,
.editor-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  min-height: 400px;
}

.list-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.editor-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.editor-title svg {
  width: 18px;
  height: 18px;
  color: var(--accent);
}

.count-badge {
  background: var(--accent-light);
  color: var(--accent);
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: none;
  background: var(--accent);
  color: white;
  border-radius: var(--radius);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition);
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary svg {
  width: 14px;
  height: 14px;
}

/* 文档列表 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px;
  color: var(--text-muted);
}

.empty-state svg {
  width: 48px;
  height: 48px;
  opacity: 0.4;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.doc-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  flex: 1;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: all var(--transition);
}

.doc-item:hover {
  background: var(--border-light);
}

.doc-item.selected {
  border-color: var(--accent);
  border-left-width: 3px;
  background: var(--accent-light);
}

.doc-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--border-light);
  border-radius: var(--radius);
  flex-shrink: 0;
}

.doc-icon svg {
  width: 20px;
  height: 20px;
  color: var(--accent);
}

.doc-main {
  flex: 1;
  min-width: 0;
}

.doc-name {
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-meta {
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.doc-meta .divider {
  color: var(--border);
}

.doc-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity var(--transition);
}

.doc-item:hover .doc-actions {
  opacity: 1;
}

.icon-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all var(--transition);
}

.icon-btn:hover {
  background: var(--border-light);
  color: var(--accent);
}

.icon-btn.danger:hover {
  background: #FEF2F2;
  color: var(--error);
}

.icon-btn svg {
  width: 14px;
  height: 14px;
}

/* 编辑器 */
.editor-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.editor-panel.empty {
  justify-content: center;
  align-items: center;
}

.editor-textarea {
  flex: 1;
  width: 100%;
  min-height: 300px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  outline: none;
  transition: border-color var(--transition), box-shadow var(--transition);
}

.editor-textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-light);
}

.preview {
  flex: 1;
  max-height: 380px;
  overflow-y: auto;
  padding: 16px;
  background: var(--border-light);
  border-radius: var(--radius);
  line-height: 1.7;
  font-size: 14px;
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
