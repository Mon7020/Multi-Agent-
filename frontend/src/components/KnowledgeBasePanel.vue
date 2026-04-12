<template>
  <div class="kb-panel">
    <div class="panel-header">
      <div>
        <h2>知识库</h2>
        <p class="header-desc">管理文档和检索配置</p>
      </div>
      <div class="header-actions">
        <button @click="reloadKnowledgeBase" class="btn btn-ghost" :disabled="loading">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6"/><path d="M1 20v-6h6"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          重新加载
        </button>
        <button @click="clearCache" class="btn btn-ghost">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
          清除缓存
        </button>
      </div>
    </div>

    <div class="panel-grid">
      <!-- 上传区域 -->
      <div class="upload-card">
        <h3>上传文档</h3>
        <div
          class="dropzone"
          :class="{ 'drag-over': isDragOver }"
          @dragover.prevent="isDragOver = true"
          @dragleave="isDragOver = false"
          @drop.prevent="handleDrop"
        >
          <div class="dropzone-content">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <p>拖拽文件到此处，或<span class="link">选择文件</span></p>
            <span class="hint">支持 .txt, .pdf, .docx</span>
          </div>
          <input
            type="file"
            accept=".txt,.pdf,.docx"
            @change="handleFileSelect"
            hidden
          />
        </div>

        <div v-if="uploading" class="upload-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
          </div>
          <span>{{ uploadProgress }}%</span>
        </div>

        <div v-if="uploadResult" :class="['upload-result', uploadResult.success ? 'success' : 'error']">
          {{ uploadResult.message }}
        </div>
      </div>

      <!-- 系统状态 -->
      <div class="stats-card">
        <h3>系统状态</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-label">缓存类型</span>
            <span class="stat-value">{{ stats.cache_type || 'N/A' }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">缓存条目</span>
            <span class="stat-value">{{ stats.cache_keys || 0 }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">检索次数</span>
            <span class="stat-value">{{ stats.total_requests || 0 }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">成功率</span>
            <span class="stat-value">{{ stats.success_rate || '0%' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="documents-card">
      <div class="documents-header">
        <h3>文档列表</h3>
        <span class="doc-count">{{ documents.length }} 个文档</span>
      </div>

      <div v-if="loading && documents.length === 0" class="loading">
        <span>加载中...</span>
      </div>

      <div v-else-if="documents.length === 0" class="empty">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        <p>暂无文档</p>
      </div>

      <div v-else class="document-list">
        <div
          v-for="doc in documents"
          :key="doc.id"
          :class="['document-item', { selected: selectedDoc?.id === doc.id }]"
          @click="selectDocument(doc)"
        >
          <div class="doc-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
          </div>
          <div class="doc-info">
            <span class="doc-name">{{ doc.filename }}</span>
            <span class="doc-meta">
              {{ formatFileSize(doc.size) }} · {{ doc.chunk_count }} 块 · {{ formatDate(doc.update_time) }}
            </span>
          </div>
          <div class="doc-actions">
            <button @click.stop="editDocument(doc)" class="icon-btn" title="编辑">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
            </button>
            <button @click.stop="deleteDocument(doc)" class="icon-btn danger" title="删除">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 文档预览/编辑 -->
    <div v-if="selectedDoc" class="editor-card">
      <div class="editor-header">
        <h3>{{ editing ? '编辑' : '预览' }}: {{ selectedDoc.filename }}</h3>
        <div class="editor-actions">
          <button v-if="!editing" @click="editDocument(selectedDoc)" class="btn btn-primary">编辑</button>
          <template v-else>
            <button @click="saveDocument" class="btn btn-primary" :disabled="saving">保存</button>
            <button @click="cancelEdit" class="btn btn-ghost">取消</button>
          </template>
          <button @click="closeEditor" class="btn btn-ghost">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </div>

      <textarea
        v-if="editing"
        v-model="editContent"
        class="editor-textarea"
        placeholder="文档内容..."
      ></textarea>
      <div v-else class="preview-content" v-html="formatContent(contentPreview)"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { knowledgeBaseApi } from '../api/index.js'

const documents = ref([])
const selectedDoc = ref(null)
const contentPreview = ref('')
const editContent = ref('')
const editing = ref(false)
const loading = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadResult = ref(null)
const saving = ref(false)
const isDragOver = ref(false)
const stats = ref({})

async function loadDocuments() {
  loading.value = true
  try {
    const res = await knowledgeBaseApi.getDocuments()
    documents.value = res.data.documents || []
  } catch (e) {
    console.error('加载文档失败:', e)
  }
  loading.value = false
}

async function loadStats() {
  try {
    const res = await knowledgeBaseApi.getParams()
    stats.value = {
      cache_type: res.data.cache_stats?.type || 'N/A',
      cache_keys: res.data.cache_stats?.keys_count || 0,
      total_requests: res.data.metrics?.total_requests || 0,
      success_rate: res.data.metrics?.success_rate || '0%'
    }
  } catch (e) {
    console.error('加载状态失败:', e)
  }
}

async function selectDocument(doc) {
  selectedDoc.value = doc
  editing.value = false

  try {
    const res = await knowledgeBaseApi.getDocument(doc.id)
    contentPreview.value = res.data.content || ''
  } catch (e) {
    console.error('加载文档失败:', e)
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
    console.error('保存失败:', e)
    alert('保存失败')
  }
  saving.value = false
}

async function deleteDocument(doc) {
  if (!confirm(`确定要删除 "${doc.filename}" 吗？`)) return

  try {
    await knowledgeBaseApi.deleteDocument(doc.id)
    await loadDocuments()
    await loadStats()
    if (selectedDoc.value?.id === doc.id) {
      selectedDoc.value = null
    }
  } catch (e) {
    console.error('删除失败:', e)
    alert('删除失败')
  }
}

async function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    await uploadFile(file)
  }
}

async function handleDrop(event) {
  isDragOver.value = false
  const file = event.dataTransfer.files[0]
  if (file) {
    await uploadFile(file)
  }
}

async function uploadFile(file) {
  uploading.value = true
  uploadProgress.value = 0
  uploadResult.value = null

  try {
    const res = await knowledgeBaseApi.uploadDocument(file)
    uploadResult.value = {
      success: true,
      message: `上传成功: ${file.name} (${res.data.chunk_count}块)`
    }
    await loadDocuments()
    await loadStats()
  } catch (e) {
    uploadResult.value = {
      success: false,
      message: '上传失败: ' + (e.response?.data?.detail || e.message)
    }
  }

  uploading.value = false
}

async function reloadKnowledgeBase() {
  loading.value = true
  try {
    await knowledgeBaseApi.reloadKnowledgeBase()
    await loadDocuments()
    await loadStats()
    alert('知识库重新加载成功')
  } catch (e) {
    alert('重新加载失败')
  }
  loading.value = false
}

async function clearCache() {
  try {
    await knowledgeBaseApi.clearCache()
    await loadStats()
    alert('缓存已清除')
  } catch (e) {
    alert('清除失败')
  }
}

function closeEditor() {
  selectedDoc.value = null
  editing.value = false
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

function formatContent(content) {
  if (!content) return ''
  return content.replace(/\n/g, '<br>')
}

onMounted(() => {
  loadDocuments()
  loadStats()
})
</script>

<style scoped>
.kb-panel {
  max-width: 1000px;
  margin: 0 auto;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.panel-header h2 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 4px;
}

.header-desc {
  font-size: 14px;
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius);
  font-size: 13px;
  font-weight: 500;
  transition: all var(--transition);
}

.btn-primary {
  background: var(--accent);
  color: white;
}

.btn-primary:hover {
  background: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border);
}

.btn-ghost:hover {
  background: var(--border-light);
  color: var(--text-primary);
}

.panel-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.upload-card, .stats-card, .documents-card, .editor-card {
  background: var(--surface);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow);
}

.upload-card h3, .stats-card h3, .documents-card h3, .editor-card h3 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.dropzone {
  border: 1px dashed var(--border);
  border-radius: var(--radius);
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition);
}

.dropzone:hover, .dropzone.drag-over {
  border-color: var(--accent);
  background: var(--accent-light);
}

.dropzone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}

.dropzone-content svg {
  color: var(--text-muted);
}

.dropzone-content p {
  font-size: 14px;
}

.dropzone-content .link {
  color: var(--accent);
  font-weight: 500;
}

.dropzone-content .hint {
  font-size: 12px;
  color: var(--text-muted);
}

.upload-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s;
}

.upload-progress span {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 36px;
}

.upload-result {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: var(--radius);
  font-size: 13px;
}

.upload-result.success {
  background: #ECFDF5;
  color: #065F46;
}

.upload-result.error {
  background: #FEF2F2;
  color: #991B1B;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stat-item {
  padding: 12px;
  background: var(--bg);
  border-radius: var(--radius);
}

.stat-label {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.documents-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.doc-count {
  font-size: 13px;
  color: var(--text-muted);
}

.loading, .empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: var(--text-muted);
  gap: 8px;
}

.empty svg {
  opacity: 0.5;
}

.document-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.document-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: all var(--transition);
}

.document-item:hover {
  border-color: var(--text-muted);
}

.document-item.selected {
  border-color: var(--accent);
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
  color: var(--text-secondary);
}

.doc-info {
  flex: 1;
  min-width: 0;
}

.doc-name {
  display: block;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-meta {
  font-size: 12px;
  color: var(--text-muted);
}

.doc-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity var(--transition);
}

.document-item:hover .doc-actions {
  opacity: 1;
}

.icon-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--text-muted);
  transition: all var(--transition);
}

.icon-btn:hover {
  background: var(--border-light);
  color: var(--text-primary);
}

.icon-btn.danger:hover {
  background: #FEF2F2;
  color: var(--error);
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.editor-header h3 {
  margin: 0;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

.editor-textarea {
  width: 100%;
  min-height: 250px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
}

.editor-textarea:focus {
  border-color: var(--accent);
}

.preview-content {
  padding: 16px;
  background: var(--bg);
  border-radius: var(--radius);
  max-height: 350px;
  overflow-y: auto;
  line-height: 1.7;
  font-size: 14px;
}

@media (max-width: 768px) {
  .panel-grid {
    grid-template-columns: 1fr;
  }
}
</style>
