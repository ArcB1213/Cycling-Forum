<template>
  <div v-show="activeTab === 'ratings'" class="tab-content">
    <div v-if="isLoading" class="loading-state">加载中...</div>
    <div v-else-if="!ratings || ratings.data.length === 0" class="empty-state">
      暂无评价记录
    </div>
    <div v-else class="ratings-list">
      <div
        v-for="rating in ratings.data"
        :key="rating.rating_id"
        class="rating-card"
        @click="$emit('go-to-rider', rating.rider_id)"
      >
        <div class="rating-card-header">
          <span class="rider-name">{{ rating.rider_name || '未知车手' }}</span>
          <span class="rating-stars">{{ getStarRating(rating.score) }}</span>
        </div>
        <p class="rating-comment">{{ rating.comment || '无文字评价' }}</p>
        <span class="rating-time">{{ formatDate(rating.created_at) }}</span>
      </div>

      <!-- 分页 -->
      <div v-if="ratings.pagination.total_pages > 1" class="pagination">
        <button
          :disabled="!ratings.pagination.has_prev"
          @click="$emit('load-page', ratings.pagination.page - 1)"
        >
          上一页
        </button>
        <span>第 {{ ratings.pagination.page }} / {{ ratings.pagination.total_pages }} 页</span>
        <button
          :disabled="!ratings.pagination.has_next"
          @click="$emit('load-page', ratings.pagination.page + 1)"
        >
          下一页
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PaginatedRatingsResponse } from '@/interfaces/types'

interface Props {
  activeTab: 'ratings' | 'posts'
  ratings: PaginatedRatingsResponse | null
  isLoading: boolean
}

defineProps<Props>()

defineEmits<{
  'go-to-rider': [riderId: number]
  'load-page': [page: number]
}>()

const getStarRating = (score: number) => {
  return '★'.repeat(score) + '☆'.repeat(5 - score)
}

const formatDate = (dateStr?: string) => {
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

.ratings-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.rating-card {
  padding: 15px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.rating-card:hover {
  background: #eff6ff;
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.rating-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.rider-name {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.rating-stars {
  color: #fbbf24;
  font-size: 14px;
}

.rating-comment {
  color: #475569;
  font-size: 14px;
  margin: 0 0 8px 0;
  line-height: 1.5;
}

.rating-time {
  font-size: 12px;
  color: #94a3b8;
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
