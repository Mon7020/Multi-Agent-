<template>
  <section class="settings-admin-page">
    <article class="hero-card">
      <div>
        <p class="eyebrow">系统设置</p>
        <h3>统一维护运行参数、权限模型与前台策略</h3>
        <p>这里集中承接原前台设置能力。管理员可以调整运行参数，并查看当前角色边界与前台只读策略。</p>
      </div>
      <button class="ghost-btn" @click="loadSummary" :disabled="loading">
        {{ loading ? '刷新中…' : '刷新设置摘要' }}
      </button>
    </article>

    <p v-if="successMessage" class="notice success">{{ successMessage }}</p>
    <p v-if="errorMessage" class="notice error">{{ errorMessage }}</p>

    <div class="settings-grid">
      <article class="panel">
        <header class="panel-head">
          <div>
            <p class="label">运行参数</p>
            <h4>后台可编辑配置</h4>
          </div>
          <button class="solid-btn" @click="saveRuntime" :disabled="saving">
            {{ saving ? '保存中…' : '保存参数' }}
          </button>
        </header>

        <div class="form-grid">
          <label>
            分块大小
            <input v-model.number="runtimeParams.chunk_size" type="number" min="100" max="1200" step="50" />
          </label>
          <label>
            分块重叠
            <input v-model.number="runtimeParams.chunk_overlap" type="number" min="0" max="400" step="10" />
          </label>
          <label>
            召回数量
            <input v-model.number="runtimeParams.top_k" type="number" min="1" max="20" />
          </label>
          <label>
            相似度阈值
            <input v-model.number="runtimeParams.similarity_threshold" type="number" min="0" max="1" step="0.05" />
          </label>
        </div>

        <div class="switch-grid">
          <label class="switch-item">
            <span>启用缓存</span>
            <input v-model="runtimeParams.enable_cache" type="checkbox" />
          </label>
          <label class="switch-item">
            <span>启用重排</span>
            <input v-model="runtimeParams.enable_rerank" type="checkbox" />
          </label>
          <label class="switch-item">
            <span>启用混合检索</span>
            <input v-model="runtimeParams.enable_hybrid" type="checkbox" />
          </label>
          <label class="switch-item">
            <span>启用 Self-RAG</span>
            <input v-model="runtimeParams.enable_self_rag" type="checkbox" />
          </label>
        </div>
      </article>

      <article class="panel">
        <header class="panel-head">
          <div>
            <p class="label">权限模型</p>
            <h4>角色职责边界</h4>
          </div>
        </header>

        <div class="role-grid">
          <div v-for="(role, key) in permissionRoles" :key="key" class="role-card">
            <strong>{{ role.label }}</strong>
            <p class="role-key">{{ key }}</p>
            <ul>
              <li v-for="item in role.capabilities" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>
      </article>

      <article class="panel full">
        <header class="panel-head">
          <div>
            <p class="label">前台策略</p>
            <h4>只读边界说明</h4>
          </div>
        </header>
        <div class="policy-grid">
          <div v-for="(value, key) in frontendPolicy" :key="key" class="policy-card">
            <strong>{{ policyLabel(key) }}</strong>
            <p>{{ value }}</p>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { settingsAdminApi } from '../../admin-api.js'

const loading = ref(false)
const saving = ref(false)
const runtimeParams = ref({
  chunk_size: 400,
  chunk_overlap: 50,
  top_k: 5,
  similarity_threshold: 0.3,
  enable_cache: true,
  enable_rerank: true,
  enable_hybrid: true,
  enable_self_rag: false
})
const permissionModel = ref({ roles: {} })
const frontendPolicy = ref({})
const errorMessage = ref('')
const successMessage = ref('')

const permissionRoles = computed(() => permissionModel.value.roles || {})

function setError(message) {
  errorMessage.value = message
  successMessage.value = ''
}

function setSuccess(message) {
  successMessage.value = message
  errorMessage.value = ''
}

async function loadSummary() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await settingsAdminApi.getSummary()
    runtimeParams.value = { ...response.data.runtime_params }
    permissionModel.value = response.data.permission_model || { roles: {} }
    frontendPolicy.value = response.data.frontend_policy || {}
  } catch (error) {
    setError(error.response?.data?.detail || error.message || '加载系统设置失败')
  } finally {
    loading.value = false
  }
}

async function saveRuntime() {
  saving.value = true
  try {
    const response = await settingsAdminApi.updateRuntime(runtimeParams.value)
    runtimeParams.value = { ...response.data.params }
    setSuccess('运行参数已保存，新的后台设置已生效')
  } catch (error) {
    setError(error.response?.data?.detail || error.message || '保存运行参数失败')
  } finally {
    saving.value = false
  }
}

function policyLabel(key) {
  const labels = {
    knowledge_base: '知识库前台策略',
    settings: '设置前台策略'
  }
  return labels[key] || key
}

onMounted(() => {
  loadSummary()
})
</script>

<style scoped>
.settings-admin-page {
  display: grid;
  gap: 18px;
}

.hero-card,
.panel {
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

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.panel {
  padding: 22px;
}

.panel.full {
  grid-column: 1 / -1;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.eyebrow,
.label,
.role-key {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.hero-card h3,
.panel h4,
.role-card strong,
.policy-card strong {
  font-family: Georgia, 'Times New Roman', serif;
}

.form-grid,
.switch-grid,
.role-grid,
.policy-grid {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.form-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.switch-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.role-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.policy-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

label,
.role-card,
.policy-card {
  padding: 16px;
  border-radius: 18px;
  background: rgba(246, 241, 233, 0.72);
}

label {
  display: grid;
  gap: 10px;
  color: var(--text-secondary);
}

input[type='number'] {
  width: 100%;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(33, 44, 66, 0.12);
  background: rgba(255, 255, 255, 0.9);
}

.switch-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.role-card ul {
  margin-top: 12px;
  padding-left: 18px;
  color: var(--text-secondary);
  line-height: 1.8;
}

.policy-card p {
  margin-top: 10px;
  color: var(--text-secondary);
  line-height: 1.7;
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

.notice.success,
.notice.error {
  padding: 14px 16px;
  border-radius: 16px;
}

.notice.success {
  background: rgba(14, 97, 90, 0.1);
  color: var(--accent);
}

.notice.error {
  background: rgba(180, 71, 55, 0.1);
  color: #9f3427;
}

@media (max-width: 960px) {
  .hero-card,
  .settings-grid,
  .form-grid,
  .switch-grid,
  .role-grid,
  .policy-grid {
    grid-template-columns: 1fr;
  }

  .hero-card {
    flex-direction: column;
  }
}
</style>
