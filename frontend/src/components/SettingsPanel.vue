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
import { onMounted, ref } from 'vue'
import { healthApi, knowledgeBaseApi, skillsApi } from '../api/index.js'

const defaultParams = {
  chunk_size: 400,
  chunk_overlap: 50,
  top_k: 5,
  similarity_threshold: 0.3,
  enable_cache: true,
  enable_rerank: true,
  enable_hybrid: true,
  enable_self_rag: false
}

const params = ref({ ...defaultParams })
const metrics = ref({})
const skillStats = ref({})
const healthStatus = ref('unknown')
const backendVersion = ref('N/A')
const skillsCount = ref(0)
const enabledSkills = ref(0)
const saving = ref(false)
const saveResult = ref(null)

async function loadParams() {
  try {
    const res = await knowledgeBaseApi.getParams()
    if (res.data.params) {
      params.value = { ...res.data.params }
    }
    metrics.value = res.data.metrics || {}
  } catch (e) {
    console.error('load params failed:', e)
  }
}

async function saveParams() {
  saving.value = true
  saveResult.value = null

  try {
    await knowledgeBaseApi.updateParams(params.value)
    saveResult.value = { success: true, message: '参数已保存并生效' }
    setTimeout(() => {
      saveResult.value = null
    }, 3000)
  } catch (e) {
    saveResult.value = { success: false, message: e.response?.data?.detail || e.message || '保存失败' }
  }

  saving.value = false
}

function resetParams() {
  if (confirm('确定重置为默认参数吗？')) {
    params.value = { ...defaultParams }
  }
}

async function loadMetrics() {
  await loadParams()
  try {
    const statsRes = await skillsApi.getStats()
    skillStats.value = statsRes.data || {}
  } catch (e) {
    console.error('load skill stats failed:', e)
    skillStats.value = {}
  }
}

function clearMetrics() {
  metrics.value = {}
  skillStats.value = {}
}

async function loadSystemInfo() {
  try {
    const [healthRes, skillsRes] = await Promise.all([
      healthApi.check(),
      skillsApi.getSkills()
    ])

    healthStatus.value = healthRes.data?.status || 'unknown'
    backendVersion.value = healthRes.data?.version || 'N/A'

    const list = skillsRes.data?.skills || []
    skillsCount.value = list.length
    enabledSkills.value = list.filter(s => !!s.enabled).length
  } catch (e) {
    console.error('load system info failed:', e)
    healthStatus.value = 'unreachable'
  }

  try {
    const statsRes = await skillsApi.getStats()
    skillStats.value = statsRes.data || {}
  } catch {
    skillStats.value = {}
  }
}

function formatRate(value) {
  if (typeof value !== 'number') return '0%'
  return `${(value * 100).toFixed(1)}%`
}

function getRateClass(value) {
  if (typeof value === 'string') {
    const num = parseFloat(value)
    if (isNaN(num)) return ''
    value = num
  }
  if (typeof value !== 'number') return ''
  if (value >= 0.8) return 'success'
  if (value >= 0.5) return 'warning'
  return 'error'
}

onMounted(async () => {
  await Promise.all([loadParams(), loadSystemInfo()])
})
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
