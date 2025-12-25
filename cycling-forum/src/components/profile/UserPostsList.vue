<template>
  <div v-show="activeTab === 'posts'" class="tab-content">
    <div v-if="isLoading" class="loading-state">加载中...</div>
    <div v-else-if="!posts || posts.data.length === 0" class="empty-state">
      暂无发帖记录
    </div>
    <div v-else class="posts-list">
      <div
        v-for="post in posts.data"
        :key="post.post_id"
        class="post-card"
        @click="$emit('go-to-post', post.post_id)"
      >
        <div class="post-card-header">
          <h4 class="post-title">{{ post.title }}</h4>
          <span class="post-time">{{ formatDateTime(post.created_at) }}</span>
        </div>
        <p class="post-preview">
          {{ post.content.substring(0, 100) }}{{ post.content.length > 100 ? '...' : '' }}
        </p>
        <div class="post-stats">
          <span>👁 {{ post.view_count }}</span>
          <span>💬 {{ post.comment_count }}</span>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="posts.pagination.total_pages > 1" class="pagination">
        <button
          :disabled="!posts.pagination.has_prev"
          @click="$emit('load-page', posts.pagination.page - 1)"
        >
          上一页
        </button>
        <span>第 {{ posts.pagination.page }} / {{ posts.pagination.total_pages }} 页</span>
        <button
          :disabled="!posts.pagination.has_next"
          @click="$emit('load-page', posts.pagination.page + 1)"
        >
          下一页
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PaginatedForumPostsResponse } from '@/interfaces/types'

interface Props {
  activeTab: 'ratings' | 'posts'
  posts: PaginatedForumPostsResponse | null
  isLoading: boolean
}

defineProps<Props>()

defineEmits<{
  'go-to-post': [postId: number]
  'load-page': [page: number]
}>()

const formatDateTime = (dateStr?: string) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.tab-content {
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.posts-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.post-card {
  padding: 20px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.post-card:hover {
  background: #eff6ff;
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.post-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  gap: 15px;
}

.post-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
  flex: 1;
}

.post-time {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
}

.post-preview {
  color: #475569;
  font-size: 14px;
  margin: 0 0 12px 0;
  line-height: 1.6;
}

.post-stats {
  display: flex;
  gap: 20px;
  font-size: 14px;
  color: #64748b;
}

.loading-state,
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #94a3b8;
  font-size: 14px;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}

.pagination button {
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s;
}

.pagination button:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #3b82f6;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination span {
  font-size: 14px;
  color: #64748b;
}
</style>
