# 前端改版实现计划

> **For agentic workers:** 使用 superpowers:subagent-driven-development (推荐) 或 superpowers:executing-plans 执行此计划。

**Goal:** 将客服系统前端升级为微暖专业风设计，保持端口和交互逻辑不变

**Architecture:** 纯前端样式改造，修改全局CSS变量和4个Vue组件的样式部分，不涉及业务逻辑

**Tech Stack:** Vue 3 + CSS Variables + 原生样式

---

## 文件映射

| 文件 | 职责 |
|------|------|
| `frontend/src/style.css` | 全局CSS变量、基础样式重置、滚动条 |
| `frontend/src/App.vue` | Header布局、Tab组件 |
| `frontend/src/components/ChatPanel.vue` | 对话气泡流、输入区 |
| `frontend/src/components/KnowledgeBasePanel.vue` | 文档列表、工具栏、编辑器 |
| `frontend/src/components/SettingsPanel.vue` | 参数表单、指标卡片 |

---

## Task 1: 更新全局样式 (style.css)

**Files:**
- Modify: `frontend/src/style.css`

- [ ] **Step 1: 更新CSS变量**

```css
:root {
  --bg: #F8F9FB;           /* 微暖灰背景 */
  --surface: #FFFFFF;
  --border: #E5E7EB;
  --border-light: #F3F4F6;
  --text-primary: #1A1A1A;
  --text-secondary: #6B7280;
  --text-muted: #9CA3AF;
  --accent: #2563EB;
  --accent-light: #EFF6FF;
  --accent-hover: #1D4ED8;
  --success: #10B981;
  --warning: #F59E0B;      /* 新增 */
  --error: #EF4444;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
  --radius: 12px;          /* 从8px改为12px */
  --radius-lg: 16px;
  --transition: 0.2s ease;
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/style.css
git commit -m "style: 更新全局CSS变量和圆角规范

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: 重构 App.vue (Header + Tab)

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 替换template和style**

```vue
<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-brand">
        <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        <h1>智能客服系统</h1>
      </div>
      <nav class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <span class="tab-icon" v-html="tab.icon"></span>
          {{ tab.label }}
        </button>
      </nav>
    </header>

    <main class="app-main">
      <ChatPanel v-if="activeTab === 'chat'" />
      <KnowledgeBasePanel v-else-if="activeTab === 'knowledge'" />
      <SettingsPanel v-else />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChatPanel from './components/ChatPanel.vue'
import KnowledgeBasePanel from './components/KnowledgeBasePanel.vue'
import SettingsPanel from './components/SettingsPanel.vue'

const activeTab = ref('chat')

const tabs = [
  {
    key: 'chat',
    label: '对话',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
  },
  {
    key: 'knowledge',
    label: '知识库',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>'
  },
  {
    key: 'settings',
    label: '设置',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v4m0 14v4m-7.07-2.93l2.83-2.83m8.48-8.48l2.83-2.83M1 12h4m14 0h4m-2.93 7.07l-2.83-2.83M6.34 6.34L3.51 3.51"/></svg>'
  }
]
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg);
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 56px;
  padding: 0 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  width: 22px;
  height: 22px;
  color: var(--accent);
}

.header-brand h1 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
}

.tabs {
  display: flex;
  gap: 4px;
}

.tabs button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border: none;
  background: transparent;
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition);
  position: relative;
}

.tabs button:hover {
  color: var(--text-primary);
  background: var(--border-light);
}

.tabs button.active {
  color: var(--accent);
  background: var(--accent-light);
  font-weight: 500;
}

.tabs button.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 2px;
  background: var(--accent);
  border-radius: 1px;
}

.tab-icon {
  display: flex;
  width: 16px;
  height: 16px;
}

.tab-icon :deep(svg) {
  width: 100%;
  height: 100%;
}

.app-main {
  flex: 1;
  padding: 24px;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/App.vue
git commit -m "style(App): 重构Header和Tab组件，使用图标+文字布局

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: 重构 ChatPanel.vue (对话气泡)

**Files:**
- Modify: `frontend/src/components/ChatPanel.vue`

- [ ] **Step 1: 替换template和style**

```vue
<template>
  <div class="chat-panel">
    <div class="messages-container" ref="messagesContainer">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['message', msg.role]"
      >
        <div class="message-bubble" v-html="formatMessage(msg.content)"></div>
        <div class="message-meta">
          <span class="time">{{ formatTime(msg.timestamp) }}</span>
          <span v-if="msg.role === 'assistant' && msg.customerType" class="tag">
            {{ msg.customerType }}
          </span>
        </div>
      </div>

      <div v-if="loading" class="message assistant">
        <div class="message-bubble typing">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </div>
    </div>

    <div class="input-area">
      <div class="input-wrapper">
        <textarea
          v-model="inputMessage"
          @keydown.enter.exact.prevent="sendMessage"
          :disabled="loading"
          rows="1"
          ref="inputTextarea"
          placeholder="输入消息，Enter 发送..."
        ></textarea>
        <button
          class="send-btn"
          @click="sendMessage"
          :disabled="loading || !inputMessage.trim()"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
      <button class="clear-btn" @click="clearHistory" :disabled="loading">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
        </svg>
        清空会话
      </button>
    </div>
  </div>
</template>

<script setup>
// ... script 保持不变，仅修改 template 和 style
</script>

<style scoped>
.chat-panel {
  height: calc(100vh - 56px - 48px);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  border-radius: var(--radius-lg);
  background: var(--surface);
  border: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  flex-direction: column;
  max-width: 75%;
}

.message.user {
  align-self: flex-end;
  align-items: flex-end;
}

.message.assistant {
  align-self: flex-start;
  align-items: flex-start;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 16px;
  line-height: 1.6;
  font-size: 14px;
  word-break: break-word;
}

.message.user .message-bubble {
  background: var(--accent);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-bubble {
  background: #F8F9FB;
  border: 1px solid #E8EAED;
  color: var(--text-primary);
  border-bottom-left-radius: 4px;
}

.message.assistant .message-bubble code {
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 13px;
}

.message.assistant .message-bubble strong {
  font-weight: 600;
}

.message.typing {
  display: flex;
  gap: 4px;
  padding: 14px 18px;
}

.message.typing .dot {
  width: 8px;
  height: 8px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}

.message.typing .dot:nth-child(1) { animation-delay: 0s; }
.message.typing .dot:nth-child(2) { animation-delay: 0.2s; }
.message.typing .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-6px); }
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.message.user .message-meta {
  flex-direction: row-reverse;
}

.message-meta .tag {
  background: var(--accent-light);
  color: var(--accent);
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
}

.input-area {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.input-wrapper {
  flex: 1;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 8px 8px 8px 16px;
  transition: border-color var(--transition), box-shadow var(--transition);
}

.input-wrapper:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-light);
}

.input-wrapper textarea {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-primary);
  padding: 4px 0;
  outline: none;
}

.input-wrapper textarea::placeholder {
  color: var(--text-muted);
}

.send-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: var(--accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition);
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: var(--accent-hover);
  transform: scale(1.05);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn svg {
  width: 18px;
  height: 18px;
}

.clear-btn {
  display: flex;
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

.clear-btn:hover:not(:disabled) {
  border-color: var(--error);
  color: var(--error);
}

.clear-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.clear-btn svg {
  width: 14px;
  height: 14px;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/ChatPanel.vue
git commit -m "style(ChatPanel): 重构对话气泡为左对齐流式布局

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: 重构 KnowledgeBasePanel.vue (知识库)

**Files:**
- Modify: `frontend/src/components/KnowledgeBasePanel.vue`

- [ ] **Step 1: 替换template和style**

```vue
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
// script 部分保持不变
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
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/KnowledgeBasePanel.vue
git commit -m "style(KnowledgeBasePanel): 重构知识库页面为卡片布局

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: 重构 SettingsPanel.vue (设置页面)

**Files:**
- Modify: `frontend/src/components/SettingsPanel.vue`

- [ ] **Step 1: 替换template和style**

```vue
<template>
  <div class="settings-panel">
    <!-- RAG 参数卡片 -->
    <section class="card">
      <div class="card-header">
        <h3>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
          RAG 参数配置
        </h3>
        <div class="action-group">
          <button class="btn-ghost" @click="resetParams">重置默认</button>
          <button class="btn-primary" @click="saveParams" :disabled="saving">
            {{ saving ? '保存中...' : '保存参数' }}
          </button>
        </div>
      </div>

      <div class="form-grid">
        <div class="form-item">
          <label>chunk_size</label>
          <input type="number" v-model.number="params.chunk_size" min="100" max="1000" step="50" />
        </div>
        <div class="form-item">
          <label>chunk_overlap</label>
          <input type="number" v-model.number="params.chunk_overlap" min="0" max="300" step="10" />
        </div>
        <div class="form-item">
          <label>top_k</label>
          <input type="number" v-model.number="params.top_k" min="1" max="30" />
        </div>
        <div class="form-item">
          <label>similarity_threshold</label>
          <input type="number" v-model.number="params.similarity_threshold" min="0" max="1" step="0.05" />
        </div>
      </div>

      <div class="switch-grid">
        <label class="switch-item">
          <span class="switch-label">enable_cache</span>
          <input type="checkbox" v-model="params.enable_cache" />
          <span class="switch-slider"></span>
        </label>
        <label class="switch-item">
          <span class="switch-label">enable_rerank</span>
          <input type="checkbox" v-model="params.enable_rerank" />
          <span class="switch-slider"></span>
        </label>
        <label class="switch-item">
          <span class="switch-label">enable_hybrid</span>
          <input type="checkbox" v-model="params.enable_hybrid" />
          <span class="switch-slider"></span>
        </label>
        <label class="switch-item">
          <span class="switch-label">enable_self_rag</span>
          <input type="checkbox" v-model="params.enable_self_rag" />
          <span class="switch-slider"></span>
        </label>
      </div>

      <div v-if="saveResult" :class="['toast', saveResult.success ? 'success' : 'error']">
        {{ saveResult.message }}
      </div>
    </section>

    <!-- 系统信息卡片 -->
    <section class="card">
      <div class="card-header">
        <h3>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
          系统信息
        </h3>
        <button class="btn-ghost" @click="loadSystemInfo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6"/><path d="M1 20v-6h6"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          刷新
        </button>
      </div>
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">后端状态</span>
          <span class="info-value" :class="healthStatus === 'ok' ? 'success' : 'error'">
            {{ healthStatus }}
          </span>
        </div>
        <div class="info-item">
          <span class="info-label">后端版本</span>
          <span class="info-value">{{ backendVersion }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">注册技能数</span>
          <span class="info-value">{{ skillsCount }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">启用技能数</span>
          <span class="info-value">{{ enabledSkills }}</span>
        </div>
      </div>
    </section>

    <!-- 运行指标卡片 -->
    <section class="card">
      <div class="card-header">
        <h3>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="20" x2="18" y2="10"/>
            <line x1="12" y1="20" x2="12" y2="4"/>
            <line x1="6" y1="20" x2="6" y2="14"/>
          </svg>
          运行指标
        </h3>
        <div class="action-group">
          <button class="btn-ghost" @click="loadMetrics">刷新</button>
          <button class="btn-ghost" @click="clearMetrics">清空</button>
        </div>
      </div>
      <div class="metrics-grid">
        <div class="metric-item">
          <span class="metric-value">{{ metrics.total_requests || 0 }}</span>
          <span class="metric-label">总请求数</span>
        </div>
        <div class="metric-item">
          <span class="metric-value" :class="getRateClass(metrics.success_rate)">
            {{ metrics.success_rate || '0%' }}
          </span>
          <span class="metric-label">成功率</span>
        </div>
        <div class="metric-item">
          <span class="metric-value">{{ metrics.cache_hit_rate || '0%' }}</span>
          <span class="metric-label">缓存命中率</span>
        </div>
        <div class="metric-item">
          <span class="metric-value">{{ metrics.avg_retrieval_latency || '0s' }}</span>
          <span class="metric-label">平均检索时延</span>
        </div>
        <div class="metric-item">
          <span class="metric-value">{{ skillStats.total_executions || 0 }}</span>
          <span class="metric-label">技能执行次数</span>
        </div>
        <div class="metric-item">
          <span class="metric-value" :class="getRateClass(formatRate(skillStats.success_rate))">
            {{ formatRate(skillStats.success_rate) }}
          </span>
          <span class="metric-label">技能成功率</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
// script 部分保持不变
</script>

<style scoped>
.settings-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-header h3 {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.card-header h3 svg {
  width: 18px;
  height: 18px;
  color: var(--accent);
}

.action-group {
  display: flex;
  gap: 8px;
}

/* 按钮 */
.btn-primary {
  padding: 8px 16px;
  border: none;
  background: var(--accent);
  color: white;
  border-radius: var(--radius);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition);
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-secondary);
  border-radius: var(--radius);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition);
}

.btn-ghost:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-light);
}

.btn-ghost svg {
  width: 14px;
  height: 14px;
}

/* 表单 */
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-item label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.form-item input {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  color: var(--text-primary);
  background: var(--surface);
  transition: all var(--transition);
  outline: none;
}

.form-item input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-light);
}

/* 开关 */
.switch-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.switch-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--border-light);
  border-radius: var(--radius);
  cursor: pointer;
  transition: background var(--transition);
}

.switch-item:hover {
  background: var(--border);
}

.switch-label {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
}

.switch-item input[type="checkbox"] {
  display: none;
}

.switch-slider {
  width: 40px;
  height: 22px;
  background: var(--border);
  border-radius: 11px;
  position: relative;
  transition: background var(--transition);
}

.switch-slider::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
  background: white;
  border-radius: 50%;
  transition: transform var(--transition);
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.switch-item input:checked + .switch-slider {
  background: var(--accent);
}

.switch-item input:checked + .switch-slider::after {
  transform: translateX(18px);
}

/* 信息网格 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  background: var(--border-light);
  border-radius: var(--radius);
}

.info-label {
  font-size: 12px;
  color: var(--text-muted);
}

.info-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.info-value.success { color: var(--success); }
.info-value.error { color: var(--error); }

/* 指标网格 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 20px;
  background: var(--border-light);
  border-radius: var(--radius);
  text-align: center;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.metric-value.success { color: var(--success); }
.metric-value.warning { color: var(--warning); }
.metric-value.error { color: var(--error); }

.metric-label {
  font-size: 12px;
  color: var(--text-muted);
}

/* Toast */
.toast {
  margin-top: 16px;
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

@media (max-width: 900px) {
  .form-grid,
  .switch-grid,
  .info-grid,
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/SettingsPanel.vue
git commit -m "style(SettingsPanel): 重构设置为卡片分组+指标可视化布局

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: 最终检查

- [ ] **Step 1: 验证所有文件**

```bash
cd frontend && npm run dev
```

在浏览器中检查：
- [ ] Header Tab 切换正常
- [ ] 对话气泡左对齐，用户消息右侧蓝色
- [ ] 知识库文档列表选中态正确
- [ ] 设置页面指标数字突出显示
- [ ] 端口保持不变

- [ ] **Step 2: 提交最终版本**

```bash
git add -A
git commit -m "style: 完成前端微暖专业风改版

- 更新全局CSS变量和圆角规范
- 重构App.vue Header和Tab组件
- 重构ChatPanel对话气泡布局
- 重构KnowledgeBasePanel文档管理布局
- 重构SettingsPanel卡片分组布局

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 自检清单

- [x] 设计覆盖所有4个组件 (App.vue, ChatPanel, KnowledgeBasePanel, SettingsPanel)
- [x] 全局变量更新在 style.css
- [x] 无 placeholder / TODO
- [x] 保持端口不变
- [x] 不修改业务逻辑
- [x] 提交粒度合理 (每个组件单独提交)
