<template>
  <div class="admin-shell">
    <aside class="sidebar">
      <div class="sidebar-header">
        <p class="eyebrow">记忆控制台</p>
        <h1>记忆管理后台</h1>
        <p class="sidebar-copy">
          独立于用户前台，用于查看、修正和清理与用户绑定的三层记忆。
        </p>
      </div>

      <div class="sidebar-toolbar">
        <input
          v-model.trim="searchText"
          class="search-input"
          type="search"
          placeholder="搜索用户 ID / 用户名"
        />
        <button class="ghost-btn" @click="loadUsers" :disabled="loadingUsers">
          {{ loadingUsers ? '刷新中...' : '刷新用户' }}
        </button>
      </div>

      <div class="user-list">
        <button
          v-for="user in filteredUsers"
          :key="user.user_id"
          :class="['user-card', { active: selectedUserId === user.user_id }]"
          @click="selectUser(user.user_id)"
        >
          <div class="user-card-top">
            <div class="user-identity">
              <span class="user-name">{{ user.username || '未设置用户名' }}</span>
              <span class="user-id">{{ user.user_id }}</span>
            </div>
            <span :class="['status-pill', user.active_in_memory ? 'online' : 'offline']">
              {{ formatPresenceStatus(user.active_in_memory) }}
            </span>
          </div>
          <div class="user-card-meta">
            <span>{{ user.total_turns }} 轮对话</span>
            <span>{{ user.medium_term_count }} 条摘要</span>
            <span>{{ user.preference_count }} 项偏好</span>
          </div>
        </button>

        <div v-if="!loadingUsers && filteredUsers.length === 0" class="sidebar-empty">
          未找到可管理的用户记忆。
        </div>
      </div>
    </aside>

    <main class="content">
      <header class="content-header">
        <div>
          <p class="eyebrow">管理面板</p>
          <h2>{{ selectedUserTitle }}</h2>
          <p v-if="selectedUserSubtitle" class="content-subtitle">{{ selectedUserSubtitle }}</p>
        </div>
        <div class="header-actions">
          <button class="ghost-btn" @click="loadSelectedUser" :disabled="!selectedUserId || loadingDetail">
            {{ loadingDetail ? '加载中...' : '刷新详情' }}
          </button>
        </div>
      </header>

      <div v-if="errorMessage" class="notice error">{{ errorMessage }}</div>
      <div v-if="successMessage" class="notice success">{{ successMessage }}</div>

      <div v-if="!selectedUserId" class="empty-panel">
        选择一个用户以查看与用户 ID 和用户名绑定的记忆。
      </div>

      <div v-else-if="loadingDetail" class="empty-panel">
        正在加载记忆详情...
      </div>

      <template v-else-if="selectedDetail">
        <section class="stats-grid">
          <article class="stat-card">
            <span class="stat-label">用户名</span>
            <strong class="stat-value">{{ selectedDetail.username || '无' }}</strong>
          </article>
          <article class="stat-card">
            <span class="stat-label">用户 ID</span>
            <strong class="stat-value">{{ selectedDetail.user_id }}</strong>
          </article>
          <article class="stat-card">
            <span class="stat-label">最近会话</span>
            <strong class="stat-value">{{ selectedDetail.context_snapshot?.session_id || '无' }}</strong>
          </article>
          <article class="stat-card">
            <span class="stat-label">对话轮次</span>
            <strong class="stat-value">{{ turnCount }}</strong>
          </article>
        </section>

        <section class="stats-grid secondary-stats">
          <article class="stat-card">
            <span class="stat-label">短期记忆</span>
            <strong class="stat-value">{{ shortTermCount }}</strong>
          </article>
          <article class="stat-card">
            <span class="stat-label">中期记忆</span>
            <strong class="stat-value">{{ mediumTermCount }}</strong>
          </article>
          <article class="stat-card">
            <span class="stat-label">偏好数量</span>
            <strong class="stat-value">{{ preferenceEntries.length }}</strong>
          </article>
          <article class="stat-card">
            <span class="stat-label">存储状态</span>
            <strong class="stat-value">{{ formatStorageStatus(selectedDetail.active_in_memory) }}</strong>
          </article>
        </section>

        <section class="panel panel-actions">
          <div>
            <h3>记忆操作</h3>
            <p>
              清除上下文会删除已持久化的会话快照。清除全部还会同时删除长期画像。
            </p>
          </div>
          <div class="panel-action-buttons">
            <button class="ghost-btn danger" @click="clearContextMemory" :disabled="actionLoading">
              清除上下文
            </button>
            <button class="solid-btn danger" @click="clearAllMemory" :disabled="actionLoading">
              清除全部记忆
            </button>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>偏好修正</h3>
              <p>将一条偏好写入长期记忆，并同步到当前上下文快照。</p>
            </div>
          </div>

          <div class="editor-grid">
            <label>
              键
              <input v-model.trim="preferenceKey" type="text" placeholder="例如：customer_type" />
            </label>
            <label>
              置信度
              <input v-model.number="preferenceConfidence" type="number" min="0" max="1" step="0.1" />
            </label>
          </div>

          <label class="editor-block">
            值
            <textarea
              v-model="preferenceValue"
              rows="4"
              placeholder="输入纯文本或 JSON"
            ></textarea>
          </label>

          <div class="editor-actions">
            <button class="solid-btn" @click="savePreference" :disabled="actionLoading || !preferenceKey">
              保存偏好
            </button>
          </div>
        </section>

        <section class="content-grid">
          <article class="panel">
            <div class="panel-header">
              <div>
                <h3>长期画像</h3>
                <p>从磁盘加载的用户偏好及相关元数据。</p>
              </div>
            </div>

            <div v-if="preferenceEntries.length === 0" class="empty-inline">暂无长期偏好。</div>
            <div v-else class="kv-list">
              <div v-for="entry in preferenceEntries" :key="entry.key" class="kv-row">
                <div>
                  <strong>{{ entry.key }}</strong>
                  <p>{{ formatPreferenceSource(entry.meta?.source) }} / {{ entry.meta?.confidence ?? '无' }}</p>
                </div>
                <code>{{ formatInlineValue(entry.value) }}</code>
              </div>
            </div>
          </article>

          <article class="panel">
            <div class="panel-header">
              <div>
                <h3>上下文元数据</h3>
                <p>与用户绑定的上下文快照一同恢复的元数据。</p>
              </div>
            </div>
            <pre class="json-block">{{ formatJson(selectedDetail.context_snapshot?.metadata || {}) }}</pre>
          </article>
        </section>

        <section class="content-grid">
          <article class="panel">
            <div class="panel-header">
              <div>
                <h3>最近对话</h3>
                <p>最近持久化的对话历史，最多显示 20 条。</p>
              </div>
            </div>
            <div v-if="recentTurns.length === 0" class="empty-inline">暂无已持久化对话。</div>
            <div v-else class="turn-list">
              <div
                v-for="turn in recentTurns"
                :key="turn.timestamp + turn.role + turn.content.slice(0, 12)"
                class="turn-card"
              >
                <div class="turn-meta">
                  <span class="turn-role">{{ formatTurnRole(turn.role) }}</span>
                  <span>{{ formatDateTime(turn.timestamp) }}</span>
                  <span v-if="turn.intent">{{ turn.intent }}</span>
                </div>
                <p>{{ turn.content }}</p>
              </div>
            </div>
          </article>

          <article class="panel">
            <div class="panel-header">
              <div>
                <h3>中期记忆</h3>
                <p>持续对话中生成的压缩摘要。</p>
              </div>
            </div>
            <div v-if="mediumMemories.length === 0" class="empty-inline">暂无中期摘要。</div>
            <div v-else class="memory-list">
              <div v-for="memory in mediumMemories" :key="memory.timestamp + memory.summary" class="memory-card">
                <strong>{{ memory.summary }}</strong>
                <p>{{ memory.discussed_topics?.join(' / ') || '无标记主题' }}</p>
                <span>{{ formatDateTime(memory.timestamp) }}</span>
              </div>
            </div>
          </article>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { memoryAdminApi } from './admin-api.js'

const users = ref([])
const selectedUserId = ref('')
const selectedDetail = ref(null)
const searchText = ref('')
const loadingUsers = ref(false)
const loadingDetail = ref(false)
const actionLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const preferenceKey = ref('')
const preferenceValue = ref('')
const preferenceConfidence = ref(1)

const filteredUsers = computed(() => {
  const keyword = searchText.value.trim().toLowerCase()
  if (!keyword) return users.value

  return users.value.filter((user) => {
    const userId = (user.user_id || '').toLowerCase()
    const username = (user.username || '').toLowerCase()
    return userId.includes(keyword) || username.includes(keyword)
  })
})

const selectedUserRecord = computed(() => (
  selectedDetail.value ||
  users.value.find((user) => user.user_id === selectedUserId.value) ||
  null
))

const selectedUserTitle = computed(() => {
  const user = selectedUserRecord.value
  if (!user) return '请选择要查看记忆的用户'
  return user.username || user.user_id
})

const selectedUserSubtitle = computed(() => {
  const user = selectedUserRecord.value
  if (!user) return ''
  if (user.username) return `用户 ID：${user.user_id}｜用户名：${user.username}`
  return `用户 ID：${user.user_id}`
})

const turnCount = computed(() => selectedDetail.value?.context_snapshot?.turn_history?.length || 0)
const shortTermCount = computed(() => (
  selectedDetail.value?.context_snapshot?.three_tier_summary?.stats?.short_term_turns || 0
))
const mediumTermCount = computed(() => (
  selectedDetail.value?.context_snapshot?.three_tier_summary?.stats?.compressed_memories || 0
))
const recentTurns = computed(() => (
  selectedDetail.value?.context_snapshot?.turn_history?.slice(-20) || []
))
const mediumMemories = computed(() => (
  selectedDetail.value?.context_snapshot?.medium_term?.compressed_memories?.slice(-10) || []
))
const preferenceEntries = computed(() => {
  const profile = selectedDetail.value?.long_term_profile || {}
  const preferences = profile.preferences || {}
  const meta = profile.preference_meta || {}
  return Object.keys(preferences).map((key) => ({
    key,
    value: preferences[key],
    meta: meta[key] || null
  }))
})

function setError(message) {
  errorMessage.value = message
  successMessage.value = ''
}

function setSuccess(message) {
  successMessage.value = message
  errorMessage.value = ''
}

function resetMessages() {
  errorMessage.value = ''
  successMessage.value = ''
}

function formatUserLabel(user) {
  if (!user) return ''
  if (user.username) return `${user.username} (${user.user_id})`
  return user.user_id
}

function formatPresenceStatus(isActive) {
  return isActive ? '内存中' : '已持久化'
}

function formatStorageStatus(isActive) {
  return isActive ? '活跃中' : '已持久化'
}

function formatPreferenceSource(source) {
  if (!source) return '未知'

  const sourceMap = {
    admin_override: '后台修正',
    llm_inference: '模型推断',
    explicit_feedback: '显式反馈',
    user_input: '用户输入'
  }

  return sourceMap[source] || source
}

function formatTurnRole(role) {
  const roleMap = {
    user: '用户',
    human: '用户',
    assistant: '助手',
    ai: '助手',
    system: '系统',
    tool: '工具'
  }

  return roleMap[role] || role
}

async function loadUsers() {
  loadingUsers.value = true
  resetMessages()

  try {
    const response = await memoryAdminApi.listUsers()
    users.value = response.data.users || []

    if (!selectedUserId.value && users.value.length > 0) {
      await selectUser(users.value[0].user_id)
    } else if (selectedUserId.value && !users.value.some((user) => user.user_id === selectedUserId.value)) {
      selectedUserId.value = ''
      selectedDetail.value = null
    }
  } catch (error) {
    setError(error.response?.data?.detail || error.message || '加载用户列表失败')
  }

  loadingUsers.value = false
}

async function loadSelectedUser() {
  if (!selectedUserId.value) return

  loadingDetail.value = true
  resetMessages()

  try {
    const response = await memoryAdminApi.getUser(selectedUserId.value)
    selectedDetail.value = response.data
  } catch (error) {
    setError(error.response?.data?.detail || error.message || '加载记忆详情失败')
  }

  loadingDetail.value = false
}

async function selectUser(userId) {
  selectedUserId.value = userId
  await loadSelectedUser()
}

function parsePreferenceValue(raw) {
  const trimmed = raw.trim()
  if (!trimmed) return ''

  try {
    return JSON.parse(trimmed)
  } catch {
    return raw
  }
}

async function savePreference() {
  if (!selectedUserId.value || !preferenceKey.value) return

  actionLoading.value = true
  resetMessages()

  try {
    await memoryAdminApi.updatePreference(selectedUserId.value, {
      key: preferenceKey.value,
      value: parsePreferenceValue(preferenceValue.value),
      confidence: preferenceConfidence.value
    })
    await Promise.all([loadUsers(), loadSelectedUser()])
    setSuccess('偏好已写入长期记忆，并同步到上下文元数据。')
  } catch (error) {
    setError(error.response?.data?.detail || error.message || '保存偏好失败')
  }

  actionLoading.value = false
}

async function clearContextMemory() {
  if (!selectedUserId.value) return
  const label = formatUserLabel(selectedUserRecord.value)
  if (!window.confirm(`确认清除 ${label} 的已持久化上下文快照吗？`)) return

  actionLoading.value = true
  resetMessages()

  try {
    await memoryAdminApi.clearContext(selectedUserId.value)
    await Promise.all([loadUsers(), loadSelectedUser()])
    setSuccess('上下文快照已清除。')
  } catch (error) {
    setError(error.response?.data?.detail || error.message || '清除上下文记忆失败')
  }

  actionLoading.value = false
}

async function clearAllMemory() {
  if (!selectedUserId.value) return
  const label = formatUserLabel(selectedUserRecord.value)
  if (!window.confirm(`确认清除 ${label} 的全部记忆吗？`)) return

  actionLoading.value = true
  resetMessages()

  try {
    const removedUserId = selectedUserId.value
    await memoryAdminApi.clearAll(removedUserId)
    await loadUsers()
    if (selectedUserId.value === removedUserId) {
      selectedUserId.value = ''
      selectedDetail.value = null
    }
    setSuccess('长期画像和上下文快照已清除。')
  } catch (error) {
    setError(error.response?.data?.detail || error.message || '清除全部记忆失败')
  }

  actionLoading.value = false
}

function formatJson(value) {
  return JSON.stringify(value, null, 2)
}

function formatInlineValue(value) {
  return typeof value === 'string' ? value : JSON.stringify(value)
}

function formatDateTime(value) {
  if (!value) return '无'
  const date = new Date(value)
  return date.toLocaleString('zh-CN')
}

onMounted(async () => {
  await loadUsers()
})
</script>

<style scoped>
.admin-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 320px 1fr;
  background:
    radial-gradient(circle at top left, rgba(10, 132, 255, 0.08), transparent 30%),
    linear-gradient(135deg, #f4efe6 0%, #f8fbff 60%, #eef4f2 100%);
}

.sidebar {
  background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
  color: #e5eef8;
  padding: 28px 22px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.sidebar-header h1,
.content-header h2,
.panel h3 {
  font-family: Georgia, 'Times New Roman', serif;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 11px;
  color: rgba(229, 238, 248, 0.68);
  margin-bottom: 8px;
}

.sidebar-header h1,
.content-header h2 {
  font-size: 28px;
  line-height: 1.1;
}

.sidebar-copy {
  margin-top: 12px;
  color: rgba(229, 238, 248, 0.72);
  font-size: 14px;
  line-height: 1.6;
}

.sidebar-toolbar {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.search-input,
.editor-grid input,
.editor-block textarea {
  width: 100%;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 14px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.9);
  color: #172033;
  outline: none;
  transition: border-color var(--transition), box-shadow var(--transition);
}

.search-input {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  border-color: rgba(255, 255, 255, 0.12);
}

.search-input::placeholder {
  color: rgba(255, 255, 255, 0.45);
}

.search-input:focus,
.editor-grid input:focus,
.editor-block textarea:focus {
  border-color: #0ea5a4;
  box-shadow: 0 0 0 3px rgba(14, 165, 164, 0.14);
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  padding-right: 4px;
}

.user-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  border-radius: 18px;
  padding: 14px;
  text-align: left;
  color: inherit;
  transition: transform var(--transition), border-color var(--transition), background var(--transition);
}

.user-card:hover {
  transform: translateY(-1px);
  border-color: rgba(14, 165, 164, 0.38);
  background: rgba(255, 255, 255, 0.08);
}

.user-card.active {
  background: linear-gradient(135deg, rgba(14, 165, 164, 0.18), rgba(59, 130, 246, 0.14));
  border-color: rgba(14, 165, 164, 0.6);
}

.user-card-top,
.user-card-meta,
.content-header,
.panel-header,
.panel-actions,
.panel-action-buttons,
.editor-grid,
.editor-actions,
.header-actions {
  display: flex;
  align-items: center;
}

.user-card-top,
.panel-header,
.content-header,
.panel-actions {
  justify-content: space-between;
}

.user-card-top {
  align-items: flex-start;
  gap: 12px;
}

.user-identity {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.user-card-meta {
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 12px;
  font-size: 12px;
  color: rgba(229, 238, 248, 0.72);
}

.user-name {
  font-size: 14px;
  font-weight: 700;
  word-break: break-word;
}

.user-id {
  font-size: 12px;
  font-weight: 600;
  color: rgba(229, 238, 248, 0.72);
  word-break: break-all;
}

.status-pill {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid transparent;
  flex-shrink: 0;
}

.status-pill.online {
  color: #bbf7d0;
  background: rgba(34, 197, 94, 0.12);
  border-color: rgba(34, 197, 94, 0.28);
}

.status-pill.offline {
  color: #e5e7eb;
  background: rgba(148, 163, 184, 0.12);
  border-color: rgba(148, 163, 184, 0.22);
}

.sidebar-empty,
.empty-inline,
.empty-panel {
  border: 1px dashed rgba(15, 23, 42, 0.14);
  border-radius: 20px;
  padding: 24px;
  color: var(--text-secondary);
  text-align: center;
  background: rgba(255, 255, 255, 0.55);
}

.sidebar-empty {
  border-color: rgba(255, 255, 255, 0.14);
  color: rgba(229, 238, 248, 0.72);
  background: rgba(255, 255, 255, 0.04);
}

.content {
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.content-header {
  gap: 16px;
}

.content-subtitle {
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  word-break: break-all;
}

.notice {
  border-radius: 16px;
  padding: 12px 16px;
  font-size: 14px;
}

.notice.error {
  background: #fff1f2;
  color: #be123c;
  border: 1px solid #fecdd3;
}

.notice.success {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.stats-grid,
.content-grid {
  display: grid;
  gap: 16px;
}

.stats-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.secondary-stats {
  margin-top: -2px;
}

.content-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.stat-card,
.panel {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.05);
}

.stat-card {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-secondary);
}

.stat-value {
  font-size: 20px;
  line-height: 1.3;
  word-break: break-word;
}

.panel {
  padding: 20px;
}

.panel-header p,
.panel-actions p {
  color: var(--text-secondary);
  margin-top: 6px;
  font-size: 13px;
}

.panel-action-buttons,
.header-actions,
.editor-actions {
  gap: 10px;
}

.editor-grid {
  gap: 12px;
  margin-top: 16px;
}

.editor-grid label,
.editor-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}

.editor-grid label {
  flex: 1;
}

.editor-block {
  margin-top: 12px;
}

.kv-list,
.turn-list,
.memory-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.kv-row,
.turn-card,
.memory-card {
  border-radius: 16px;
  padding: 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.kv-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.kv-row p,
.turn-card p,
.memory-card p {
  margin-top: 6px;
  color: var(--text-secondary);
}

.kv-row code {
  max-width: 50%;
  white-space: pre-wrap;
  word-break: break-word;
}

.turn-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  color: var(--text-muted);
  font-size: 12px;
}

.turn-role {
  color: #0f766e;
  font-weight: 700;
  text-transform: uppercase;
}

.memory-card span {
  display: inline-block;
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.json-block {
  margin: 0;
  padding: 16px;
  border-radius: 16px;
  background: #0f172a;
  color: #dbeafe;
  font-size: 12px;
  line-height: 1.6;
  overflow: auto;
}

.ghost-btn,
.solid-btn {
  border-radius: 14px;
  padding: 11px 16px;
  font-size: 13px;
  font-weight: 600;
  transition: transform var(--transition), border-color var(--transition), background var(--transition);
}

.ghost-btn {
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.7);
  color: #172033;
}

.ghost-btn:hover:not(:disabled),
.solid-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.solid-btn {
  border: none;
  background: linear-gradient(135deg, #0f766e, #2563eb);
  color: white;
}

.ghost-btn.danger,
.solid-btn.danger {
  background-image: none;
}

.ghost-btn.danger {
  border-color: rgba(190, 24, 93, 0.18);
  color: #be123c;
  background: #fff1f2;
}

.solid-btn.danger {
  background: linear-gradient(135deg, #be123c, #ef4444);
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

@media (max-width: 1180px) {
  .admin-shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
}

@media (max-width: 900px) {
  .stats-grid,
  .content-grid,
  .editor-grid {
    grid-template-columns: 1fr;
  }

  .content {
    padding: 18px;
  }

  .content-header,
  .panel-actions,
  .kv-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .kv-row code {
    max-width: 100%;
  }
}
</style>
