<template>
  <div class="settings-panel">
    <div class="panel-header">
      <div>
        <h2>系统设置</h2>
        <p class="header-desc">配置 RAG 检索参数和功能开关</p>
      </div>
    </div>

    <!-- RAG 参数配置 -->
    <div class="settings-section">
      <h3>RAG 参数配置</h3>
      <p class="section-desc">调整检索增强生成的参数以优化系统性能</p>

      <div class="params-grid">
        <div class="param-card">
          <div class="param-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            <span>文档分割</span>
          </div>
          <div class="param-row">
            <label>块大小 (chunk_size)</label>
            <div class="slider-group">
              <input
                type="range"
                v-model.number="params.chunk_size"
                min="100"
                max="1000"
                step="50"
              />
              <span class="slider-value">{{ params.chunk_size }}</span>
            </div>
            <p class="param-hint">每个文档块包含的字符数</p>
          </div>
          <div class="param-row">
            <label>重叠长度 (chunk_overlap)</label>
            <div class="slider-group">
              <input
                type="range"
                v-model.number="params.chunk_overlap"
                min="0"
                max="200"
                step="10"
              />
              <span class="slider-value">{{ params.chunk_overlap }}</span>
            </div>
            <p class="param-hint">相邻块之间的重叠字符数</p>
          </div>
        </div>

        <div class="param-card">
          <div class="param-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <span>检索设置</span>
          </div>
          <div class="param-row">
            <label>返回数量 (top_k)</label>
            <div class="slider-group">
              <input
                type="range"
                v-model.number="params.top_k"
                min="1"
                max="20"
                step="1"
              />
              <span class="slider-value">{{ params.top_k }}</span>
            </div>
            <p class="param-hint">每次检索返回的最相似文档数量</p>
          </div>
          <div class="param-row">
            <label>相似度阈值</label>
            <div class="slider-group">
              <input
                type="range"
                v-model.number="params.similarity_threshold"
                min="0"
                max="1"
                step="0.05"
              />
              <span class="slider-value">{{ params.similarity_threshold.toFixed(2) }}</span>
            </div>
            <p class="param-hint">低于此值的文档被视为不相关</p>
          </div>
        </div>

        <div class="param-card">
          <div class="param-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
            </svg>
            <span>功能开关</span>
          </div>
          <div class="toggle-row">
            <div>
              <label>启用缓存</label>
              <p class="param-hint">使用Redis缓存检索结果</p>
            </div>
            <label class="toggle">
              <input type="checkbox" v-model="params.enable_cache" />
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="toggle-row">
            <div>
              <label>启用 Rerank</label>
              <p class="param-hint">使用交叉编码器精细排序</p>
            </div>
            <label class="toggle">
              <input type="checkbox" v-model="params.enable_rerank" />
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="toggle-row">
            <div>
              <label>启用混合检索 (BM25)</label>
              <p class="param-hint">结合向量和关键词检索</p>
            </div>
            <label class="toggle">
              <input type="checkbox" v-model="params.enable_hybrid" />
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="toggle-row">
            <div>
              <label>启用 Self-RAG</label>
              <p class="param-hint">由LLM判断是否需要检索</p>
            </div>
            <label class="toggle">
              <input type="checkbox" v-model="params.enable_self_rag" />
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>

      <div class="param-actions">
        <button @click="resetParams" class="btn btn-ghost">重置默认</button>
        <button @click="saveParams" class="btn btn-primary" :disabled="saving">
          {{ saving ? '保存中...' : '保存设置' }}
        </button>
      </div>

      <div v-if="saveResult" :class="['save-result', saveResult.success ? 'success' : 'error']">
        {{ saveResult.message }}
      </div>
    </div>

    <!-- 系统信息 -->
    <div class="settings-section">
      <h3>系统信息</h3>
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">版本</span>
          <span class="info-value">v1.0.0</span>
        </div>
        <div class="info-item">
          <span class="info-label">模型</span>
          <span class="info-value">all-MiniLM-L6-v2</span>
        </div>
        <div class="info-item">
          <span class="info-label">向量维度</span>
          <span class="info-value">384</span>
        </div>
        <div class="info-item">
          <span class="info-label">向量数据库</span>
          <span class="info-value">ChromaDB</span>
        </div>
      </div>
    </div>

    <!-- 性能指标 -->
    <div class="settings-section">
      <h3>性能指标</h3>
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-value">{{ metrics.total_requests || 0 }}</div>
          <div class="metric-label">总请求数</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{{ metrics.success_rate || '0%' }}</div>
          <div class="metric-label">成功率</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{{ metrics.cache_hit_rate || '0%' }}</div>
          <div class="metric-label">缓存命中率</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{{ metrics.avg_retrieval_latency || '0ms' }}</div>
          <div class="metric-label">平均延迟</div>
        </div>
      </div>

      <div class="metric-actions">
        <button @click="loadMetrics" class="btn btn-ghost">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6"/><path d="M1 20v-6h6"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          刷新
        </button>
        <button @click="clearMetrics" class="btn btn-ghost">清除统计</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { knowledgeBaseApi } from '../api/index.js'

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
const saving = ref(false)
const saveResult = ref(null)

async function loadParams() {
  try {
    const res = await knowledgeBaseApi.getParams()
    if (res.data.params) {
      params.value = { ...res.data.params }
    }
    if (res.data.metrics) {
      metrics.value = res.data.metrics
    }
  } catch (e) {
    console.error('加载参数失败:', e)
  }
}

async function saveParams() {
  saving.value = true
  saveResult.value = null

  try {
    await knowledgeBaseApi.updateParams(params.value)
    saveResult.value = { success: true, message: '设置已保存' }
    setTimeout(() => { saveResult.value = null }, 3000)
  } catch (e) {
    saveResult.value = { success: false, message: '保存失败: ' + e.message }
  }

  saving.value = false
}

function resetParams() {
  if (confirm('确定要重置为默认参数吗？')) {
    params.value = { ...defaultParams }
  }
}

async function loadMetrics() {
  try {
    const res = await knowledgeBaseApi.getParams()
    metrics.value = res.data.metrics || {}
  } catch (e) {
    console.error('加载指标失败:', e)
  }
}

function clearMetrics() {
  if (confirm('确定要清除所有性能统计吗？')) {
    metrics.value = {}
    alert('统计已清除')
  }
}

onMounted(() => {
  loadParams()
})
</script>

<style scoped>
.settings-panel {
  max-width: 900px;
  margin: 0 auto;
}

.panel-header {
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

.settings-section {
  background: var(--surface);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: var(--shadow);
}

.settings-section h3 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
}

.section-desc {
  margin-bottom: 20px;
  color: var(--text-secondary);
  font-size: 14px;
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

.param-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
}

.param-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.param-header svg {
  color: var(--text-muted);
}

.param-row {
  margin-bottom: 16px;
}

.param-row label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
}

.param-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.slider-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slider-group input[type="range"] {
  flex: 1;
  height: 4px;
  -webkit-appearance: none;
  background: var(--border);
  border-radius: 2px;
}

.slider-group input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: var(--accent);
  border-radius: 50%;
  cursor: pointer;
  transition: transform var(--transition);
}

.slider-group input[type="range"]::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.slider-value {
  min-width: 44px;
  text-align: right;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
}

.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light);
}

.toggle-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.toggle-row label {
  margin-bottom: 0;
  font-weight: 500;
}

.toggle {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
  flex-shrink: 0;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background-color: var(--border);
  transition: 0.25s;
  border-radius: 22px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.25s;
  border-radius: 50%;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.toggle input:checked + .toggle-slider {
  background-color: var(--accent);
}

.toggle input:checked + .toggle-slider:before {
  transform: translateX(18px);
}

.param-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border: none;
  border-radius: var(--radius);
  font-size: 14px;
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

.save-result {
  margin-top: 16px;
  padding: 12px 16px;
  border-radius: var(--radius);
  font-size: 14px;
}

.save-result.success {
  background: #ECFDF5;
  color: #065F46;
}

.save-result.error {
  background: #FEF2F2;
  color: #991B1B;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.info-item {
  padding: 16px;
  background: var(--bg);
  border-radius: var(--radius);
}

.info-label {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.info-value {
  font-weight: 600;
  font-size: 14px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  padding: 20px;
  background: var(--text-primary);
  border-radius: var(--radius);
  text-align: center;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: white;
  margin-bottom: 4px;
}

.metric-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.metric-actions {
  display: flex;
  gap: 8px;
}

@media (max-width: 768px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
