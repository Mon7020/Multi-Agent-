<template>
  <div class="chat-panel">
    <div class="chat-main">
      <div class="messages-container" ref="messagesContainer">
        <div v-if="messages.length === 0" class="welcome">
          <div class="welcome-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <h3>开始对话</h3>
          <p>输入您的问题，智能客服将基于知识库为您提供答案</p>
        </div>

        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message', msg.role]"
        >
          <div class="message-avatar">
            <svg v-if="msg.role === 'user'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
              <path d="M12 2a7 7 0 0 1 7 7"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </div>
          <div class="message-content">
            <div class="message-bubble" v-html="formatMessage(msg.content)"></div>
            <div class="message-meta">
              <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
              <span v-if="msg.role === 'assistant' && msg.customerType" class="message-tag">
                {{ msg.customerType }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="loading" class="message assistant">
          <div class="message-avatar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
              <path d="M12 2a7 7 0 0 1 7 7"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </div>
          <div class="message-content">
            <div class="message-bubble typing">
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <div class="input-wrapper">
          <textarea
            v-model="inputMessage"
            @keydown.enter.exact.prevent="sendMessage"
            placeholder="输入消息..."
            :disabled="loading"
            rows="1"
            ref="inputTextarea"
          ></textarea>
          <button
            @click="sendMessage"
            :disabled="loading || !inputMessage.trim()"
            class="send-button"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
        <div class="input-footer">
          <span>按 Enter 发送</span>
          <button @click="clearHistory" class="clear-btn">清空对话</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { chatApi } from '../api/index.js'

const messages = ref([])
const inputMessage = ref('')
const loading = ref(false)
const sessionId = ref('session_' + Date.now())
const messagesContainer = ref(null)
const inputTextarea = ref(null)

// 默认招呼消息（页面加载时直接显示）
const defaultGreeting = '您好呀！我是您的智能客服助手，可以帮您查产品、问价格、了解优惠、查物流，还可以解答使用问题哦～有什么想问的尽管说！'

onMounted(() => {
  // 页面加载时，自动显示招呼消息
  messages.value.push({
    role: 'assistant',
    content: defaultGreeting,
    timestamp: new Date().toISOString()
  })

  // 聚焦输入框
  if (inputTextarea.value) {
    inputTextarea.value.focus()
  }
})

async function sendMessage() {
  if (!inputMessage.value.trim() || loading.value) return

  const userMessage = {
    role: 'user',
    content: inputMessage.value,
    timestamp: new Date().toISOString()
  }

  messages.value.push(userMessage)
  const currentMessage = inputMessage.value
  inputMessage.value = ''
  loading.value = true

  await nextTick()
  scrollToBottom()

  try {
    const history = messages.value.slice(0, -1).map(m => ({
      role: m.role,
      content: m.content
    }))

    const response = await chatApi.sendMessage(
      sessionId.value,
      currentMessage,
      history
    )

    const assistantMessage = {
      role: 'assistant',
      content: response.data.message,
      timestamp: new Date().toISOString(),
      customerType: response.data.customer_type
    }

    // 如果有新会话招呼消息，先显示招呼，再显示回复
    if (response.data.greeting) {
      const greetingMessage = {
        role: 'assistant',
        content: response.data.greeting,
        timestamp: new Date().toISOString(),
        customerType: response.data.customer_type
      }
      messages.value.push(greetingMessage)
    }

    messages.value.push(assistantMessage)

    if (response.data.sources && response.data.sources.length > 0) {
      console.log('Sources:', response.data.sources)
    }

  } catch (error) {
    console.error('发送消息失败:', error)
    messages.value.push({
      role: 'assistant',
      content: '抱歉，发生了错误：' + (error.response?.data?.detail || error.message),
      timestamp: new Date().toISOString()
    })
  }

  loading.value = false
  await nextTick()
  scrollToBottom()
}

function formatMessage(content) {
  if (!content) return ''
  return content
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

async function clearHistory() {
  if (!confirm('确定要清空所有对话历史吗？')) return

  try {
    await chatApi.clearHistory(sessionId.value)
    messages.value = []
  } catch (error) {
    console.error('清空历史失败:', error)
  }
}
</script>

<style scoped>
.chat-panel {
  height: 100%;
  display: flex;
  justify-content: center;
}

.chat-main {
  width: 100%;
  max-width: 800px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: var(--text-secondary);
}

.welcome-icon {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--border-light);
  border-radius: 50%;
  margin-bottom: 20px;
  color: var(--text-muted);
}

.welcome h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.welcome p {
  font-size: 14px;
  max-width: 300px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message.assistant .message-avatar {
  background: var(--accent-light);
  color: var(--accent);
}

.message.user .message-avatar {
  background: var(--text-primary);
  color: white;
}

.message-content {
  max-width: 75%;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 16px;
  line-height: 1.6;
  font-size: 14px;
}

.message.assistant .message-bubble {
  background: var(--border-light);
  color: var(--text-primary);
  border-bottom-left-radius: 4px;
}

.message.user .message-bubble {
  background: var(--accent);
  color: white;
  border-bottom-right-radius: 4px;
}

.message-bubble code {
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 13px;
}

.message.user .message-bubble code {
  background: rgba(255, 255, 255, 0.2);
}

.message-bubble strong {
  font-weight: 600;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  padding: 0 4px;
}

.message.user .message-meta {
  flex-direction: row-reverse;
}

.message-time {
  font-size: 12px;
  color: var(--text-muted);
}

.message-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--border-light);
  border-radius: 4px;
  color: var(--text-secondary);
}

.typing {
  display: flex;
  gap: 4px;
  padding: 16px 20px;
}

.typing-dot {
  width: 6px;
  height: 6px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-4px); opacity: 1; }
}

.input-area {
  padding: 16px 24px 12px;
  border-top: 1px solid var(--border);
}

.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-wrapper textarea {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  outline: none;
  transition: border-color var(--transition);
  background: var(--bg);
}

.input-wrapper textarea:focus {
  border-color: var(--accent);
}

.send-button {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius);
  transition: all var(--transition);
}

.send-button:hover:not(:disabled) {
  background: var(--accent-hover);
}

.send-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  padding: 0 4px;
}

.input-footer span {
  font-size: 12px;
  color: var(--text-muted);
}

.clear-btn {
  background: none;
  border: none;
  font-size: 12px;
  color: var(--text-muted);
  padding: 4px 8px;
  border-radius: 4px;
  transition: all var(--transition);
}

.clear-btn:hover {
  background: var(--border-light);
  color: var(--error);
}
</style>
