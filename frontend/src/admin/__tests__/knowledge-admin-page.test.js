import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import KnowledgeAdminPage from '../pages/KnowledgeAdminPage.vue'
import { knowledgeAdminApi } from '../../admin-api.js'
import { getAuthUser } from '../../auth/session.js'

vi.mock('../../admin-api.js', () => ({
  knowledgeAdminApi: {
    listDocuments: vi.fn(),
    getDocument: vi.fn(),
    createDocument: vi.fn(),
    updateDocument: vi.fn(),
    replaceDocument: vi.fn(),
    deleteDocument: vi.fn(),
    restoreDocument: vi.fn()
  }
}))

vi.mock('../../auth/session.js', () => ({
  getAuthUser: vi.fn()
}))

describe('KnowledgeAdminPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders document metrics and keeps operator in read-only mode', async () => {
    getAuthUser.mockReturnValue({ role: 'operator' })
    knowledgeAdminApi.listDocuments.mockResolvedValue({
      data: {
        documents: [
          {
            document_id: 'doc_alpha',
            filename: 'alpha.txt',
            file_type: '.txt',
            size: 1024,
            chunk_count: 4,
            description: 'alpha doc',
            tags: ['faq'],
            published: true,
            visible_to_frontend: true,
            allowed_roles: ['user', 'admin'],
            deleted: false,
            updated_at: '2026-04-15T12:00:00'
          }
        ],
        total: 1
      }
    })

    const wrapper = mount(KnowledgeAdminPage)
    await flushPromises()

    expect(wrapper.text()).toContain('alpha.txt')
    expect(wrapper.text()).toContain('4 个分块')
    expect(wrapper.text()).toContain('运营只读')
    expect(wrapper.get('[data-testid="knowledge-upload-trigger"]').attributes('disabled')).toBeDefined()
  })

  it('lets admin filter deleted documents and exposes action buttons', async () => {
    getAuthUser.mockReturnValue({ role: 'admin' })
    knowledgeAdminApi.listDocuments.mockResolvedValue({
      data: {
        documents: [
          {
            document_id: 'doc_deleted',
            filename: 'deleted.txt',
            file_type: '.txt',
            size: 256,
            chunk_count: 1,
            description: 'deleted doc',
            tags: ['archive'],
            published: false,
            visible_to_frontend: false,
            allowed_roles: ['admin'],
            deleted: true,
            updated_at: '2026-04-15T12:30:00'
          }
        ],
        total: 1
      }
    })

    const wrapper = mount(KnowledgeAdminPage)
    await flushPromises()

    expect(wrapper.get('[data-testid="knowledge-status-filter"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="knowledge-upload-trigger"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).toContain('已删除')
    expect(wrapper.text()).toContain('恢复文档')
  })
})
