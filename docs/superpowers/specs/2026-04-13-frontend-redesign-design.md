# 前端改版设计方案

## 1. 概述

将现有客服系统前端升级为**微暖专业风**设计语言，对标大厂产品设计水准。保持端口不变，优化视觉层次、交互反馈和组件一致性。

## 2. 设计风格 — 微暖专业风

### 色彩系统
| Token | 色值 | 用途 |
|-------|------|------|
| `--bg` | `#F8F9FB` | 页面背景（微暖灰） |
| `--surface` | `#FFFFFF` | 卡片/面板背景 |
| `--border` | `#E5E7EB` | 边框/分割线 |
| `--accent` | `#2563EB` | 主色-蓝 |
| `--accent-light` | `#EFF6FF` | 主色浅底 |
| `--accent-hover` | `#1D4ED8` | 主色hover |
| `--success` | `#10B981` | 成功/指标正 |
| `--warning` | `#F59E0B` | 警示/高亮（新增） |
| `--error` | `#EF4444` | 错误/危险 |
| `--text-primary` | `#1A1A1A` | 主文字 |
| `--text-secondary` | `#6B7280` | 次要文字 |
| `--text-muted` | `#9CA3AF` | 辅助/占位符 |

### 圆角与间距
- `radius`: `12px`（全局卡片/按钮/输入框）
- `radius-lg`: `16px`（消息气泡）
- 间距基准: `8px` 网格（`8/16/24/32px`）

### 阴影
- `shadow-sm`: `0 1px 2px rgba(0,0,0,0.04)` — 默认卡片
- `shadow`: `0 2px 8px rgba(0,0,0,0.06)` — hover/悬浮
- `shadow-md`: `0 4px 12px rgba(0,0,0,0.08)` — 弹窗/高亮

## 3. 页面布局

### Header
- 高度 `56px`，白色背景，底部 `1px solid var(--border)`
- 左侧: 系统标题 "智能客服系统"，`18px` 字体
- 右侧: Tab 按钮，激活态 `blue` 色 + `2px` 下划线
- Tab 间距 `4px`，按钮 `padding: 6px 16px`

### 主内容区
- `padding: 24px`
- 最大宽度无限制，撑满容器

## 4. 组件规范

### 按钮
- **主按钮**: `background: var(--accent)`, `color: white`, `border-radius: 8px`
- **次按钮**: `background: white`, `border: 1px solid var(--border)`, `color: var(--text-primary)`
- **危险按钮**: `background: white`, `border: 1px solid var(--error)`, `color: var(--error)`
- **通用**: `padding: 8px 16px`, `font-size: 14px`, hover 时 `shadow` 提升
- **disabled**: `opacity: 0.5`, `cursor: not-allowed`

### 输入框 / Textarea
- `border: 1px solid var(--border)`, `border-radius: 8px`
- `padding: 10px 12px`
- Focus: `border-color: var(--accent)`, `outline: none`, `box-shadow: 0 0 0 3px var(--accent-light)`

### 卡片
- `background: var(--surface)`, `border-radius: 12px`
- `border: 1px solid var(--border)` 或仅阴影
- `padding: 20px`

### 徽章 (Badge)
- `border-radius: 999px` (pill形状)
- `padding: 4px 12px`
- `font-size: 12px`
- 状态色: success/warning/error 对应背景色淡底 + 文字色

## 5. 页面详细设计

### 5.1 对话页面 (ChatPanel)

**消息列表**
- `border-radius: 12px`, `background: var(--surface)`
- `padding: 20px`
- 消息间距: `16px`

**消息气泡**
- 用户消息: 右侧对齐，`background: var(--accent)`, `color: white`，`border-radius: 16px 16px 4px 16px`
- AI消息: 左侧对齐，`background: #F8F9FB`，`border: 1px solid #E8EAED`，`border-radius: 16px 16px 16px 4px`
- 气泡 `max-width: 70%`, `padding: 12px 16px`
- 时间戳: 气泡下方，`12px`，`var(--text-muted)`，用户消息右侧，用户消息左侧

**输入区**
- Textarea: `border-radius: 12px`, `border: 1px solid var(--border)`
- 发送按钮: 右侧，主按钮样式
- 清空会话按钮: 次按钮样式，左侧

### 5.2 知识库页面 (KnowledgeBasePanel)

**工具栏**
- 横向排列: 文件上传 input + 两个操作按钮
- `gap: 12px`

**统计栏**
- `4` 个指标徽章横向排列
- 徽章样式: pill 形状，带图标

**文档列表 (左侧)**
- 卡片列表，每项:
  - 文件名粗体 + 元信息小字
  - 操作按钮悬浮显示
  - 选中态: `border-left: 3px solid var(--accent)`

**文档编辑器 (右侧)**
- 白色卡片
- 编辑/保存/取消按钮组右上角

### 5.3 设置页面 (SettingsPanel)

**参数卡片**
- 标题 `h3: 16px` 粗体
- 双列网格布局 (`grid-template-columns: 1fr 1fr`)
- 每参数: 左侧标签 `14px`，右侧输入控件
- Switch 开关横向排列，`gap: 16px`

**指标卡片**
- 数字突出: `font-size: 28px`，`font-weight: 600`
- 指标项: 网格布局，每项带图标 + 数值 + 标签
- 成功率 > 90% 用 success 色，< 70% 用 error 色

**操作按钮组**
- 底部横向排列

## 6. 实现文件

- `frontend/src/style.css` — 全局 CSS 变量和基础样式
- `frontend/src/App.vue` — Header + 布局
- `frontend/src/components/ChatPanel.vue` — 对话面板
- `frontend/src/components/KnowledgeBasePanel.vue` — 知识库面板
- `frontend/src/components/SettingsPanel.vue` — 设置面板

## 7. 约束

- 端口保持不变
- 不修改 API 接口
- 不增加新依赖
- 保持所有交互逻辑不变，仅改视觉和布局
