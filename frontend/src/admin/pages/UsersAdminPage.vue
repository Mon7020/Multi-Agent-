<template>
  <section class="users-page">
    <article class="hero-card">
      <div>
        <p class="eyebrow">账号管理</p>
        <h3>统一管理后台账号角色</h3>
        <p>当前阶段支持账号列表与角色变更，角色更新权限限定为超级管理员。</p>
      </div>
      <button class="ghost-btn" @click="loadUsers" :disabled="loading">{{ loading ? '刷新中…' : '刷新列表' }}</button>
    </article>

    <article class="filters-card">
      <label>
        搜索账号
        <input v-model.trim="filters.q" placeholder="用户名 / 用户 ID" />
      </label>
      <label>
        角色
        <select v-model="filters.role">
          <option value="">全部</option>
          <option value="user">普通用户</option>
          <option value="operator">运营员</option>
          <option value="admin">管理员</option>
          <option value="super_admin">超级管理员</option>
        </select>
      </label>
      <label>
        状态
        <select v-model="filters.status">
          <option value="">全部</option>
          <option value="active">启用</option>
          <option value="disabled">停用</option>
        </select>
      </label>
      <button class="ghost-btn" @click="loadUsers">应用筛选</button>
    </article>

    <article class="table-card">
      <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
      <table v-else>
        <thead>
          <tr>
            <th>用户名</th>
            <th>用户 ID</th>
            <th>状态</th>
            <th>角色</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in users" :key="item.user_id">
            <td>{{ item.username || '未命名账号' }}</td>
            <td class="mono">{{ item.user_id }}</td>
            <td>{{ item.status === 'active' ? '启用' : item.status }}</td>
            <td>
              <select v-model="draftRoles[item.user_id]" :disabled="!canEditRoles">
                <option value="user">普通用户</option>
                <option value="operator">运营员</option>
                <option value="admin">管理员</option>
                <option value="super_admin">超级管理员</option>
              </select>
            </td>
            <td>
              <button class="ghost-btn" :disabled="!canEditRoles || savingId === item.user_id" @click="saveRole(item.user_id)">
                {{ savingId === item.user_id ? '保存中…' : '保存角色' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </article>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { userAdminApi } from '../../admin-api.js'
import { getAuthUser } from '../../auth/session.js'

const currentUser = getAuthUser() || {}
const canEditRoles = computed(() => currentUser.role === 'super_admin')
const filters = ref({ q: '', role: '', status: '' })
const users = ref([])
const draftRoles = ref({})
const loading = ref(false)
const savingId = ref('')
const errorMessage = ref('')

async function loadUsers() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await userAdminApi.listUsers(filters.value)
    users.value = response.data.users || []
    draftRoles.value = Object.fromEntries(users.value.map((item) => [item.user_id, item.role]))
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || error.message || '加载账号列表失败'
  } finally {
    loading.value = false
  }
}

async function saveRole(userId) {
  savingId.value = userId
  errorMessage.value = ''
  try {
    await userAdminApi.updateRole(userId, draftRoles.value[userId])
    await loadUsers()
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || error.message || '更新角色失败'
  } finally {
    savingId.value = ''
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.users-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.hero-card,
.filters-card,
.table-card {
  padding: 24px;
  border-radius: 24px;
  background: rgba(255, 252, 247, 0.84);
  border: 1px solid rgba(33, 44, 66, 0.08);
  box-shadow: 0 16px 40px rgba(33, 44, 66, 0.08);
}

.hero-card,
.filters-card {
  display: flex;
  justify-content: space-between;
  gap: 14px;
}

.filters-card {
  align-items: flex-end;
  flex-wrap: wrap;
}

label {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 180px;
  color: var(--text-secondary);
  font-size: 13px;
}

input,
select {
  padding: 11px 12px;
  border-radius: 14px;
  border: 1px solid rgba(33, 44, 66, 0.12);
  background: rgba(255, 255, 255, 0.9);
}

.eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-muted);
}

h3 {
  margin-top: 10px;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 30px;
}

p {
  margin-top: 10px;
  color: var(--text-secondary);
  line-height: 1.7;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 14px 12px;
  border-bottom: 1px solid rgba(33, 44, 66, 0.08);
  text-align: left;
}

th {
  font-size: 12px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.mono {
  font-family: 'Consolas', 'Courier New', monospace;
}

.ghost-btn {
  padding: 12px 16px;
  border-radius: 999px;
  border: 1px solid rgba(16, 98, 89, 0.16);
  background: rgba(255, 255, 255, 0.82);
  font-weight: 600;
}

.error-text {
  margin-bottom: 14px;
  color: #b42318;
}

@media (max-width: 980px) {
  .hero-card,
  .filters-card {
    flex-direction: column;
    align-items: stretch;
  }

  .table-card {
    overflow-x: auto;
  }
}
</style>
