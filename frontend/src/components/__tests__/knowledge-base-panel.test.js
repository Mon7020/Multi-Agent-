import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import KnowledgeBasePanel from '../KnowledgeBasePanel.vue'
import { knowledgeBaseApi } from '../../api/index.js'

vi.mock('../../api/index.js', () => ({
  knowledgeBaseApi: {
    getDocuments: vi.fn(),
    getDocument: vi.fn()
  }
}))

describe('KnowledgeBasePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders registry-backed metrics and loads detail by document id', async () => {
    knowledgeBaseApi.getDocuments.mockResolvedValue({
      data: {
        documents: [
          {
            id: 'doc_alpha',
            filename: 'alpha.txt',
            file_path: 'D:/docs/alpha.txt',
            file_type: '.txt',
            chunk_count: 4,
            size: 1024,
            upload_time: '2026-04-15T12:00:00',
            update_time: '2026-04-15T12:30:00'
          }
        ],
        total: 1
      }
    })
    knowledgeBaseApi.getDocument.mockResolvedValue({
      data: {
        id: 'doc_alpha',
        filename: 'alpha.txt',
        content: 'alpha body',
        chunks: []
      }
    })

    const wrapper = mount(KnowledgeBasePanel)
    await flushPromises()

    expect(knowledgeBaseApi.getDocument).toHaveBeenCalledWith('doc_alpha')
    expect(wrapper.text()).toContain('alpha.txt')
    expect(wrapper.text()).toContain('4 个分块')
    expect(wrapper.text()).toContain('文件类型：.txt')
    expect(wrapper.text()).toContain('文档 ID：doc_alpha')
    expect(wrapper.text()).toContain('alpha body')
  })
})
