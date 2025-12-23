<template>
  <div :class="['comment-item', depth > 0 ? 'reply' : 'floor']">
    <div class="comment-header">
      <img :src="getAvatarUrl(comment.author_avatar)" class="avatar" />
      <div class="comment-meta">
        <span class="author">{{ comment.author_nickname || '未知用户' }}</span>
        <span v-if="comment.floor_number" class="floor-number">#{{ comment.floor_number }}</span>
        <span class="time">{{ formatTime(comment.created_at) }}</span>
      </div>
    </div>

    <div class="comment-content">{{ comment.content }}</div>

    <div class="comment-actions">
      <button @click="handleReply" class="btn-reply">回复</button>
      <button v-if="isCommentAuthor()" @click="handleDelete" class="btn-delete" title="删除">
        ❌
      </button>
    </div>

    <!-- 递归渲染子回复 -->
    <div v-if="comment.replies?.length" class="replies">
      <CommentItem
        v-for="reply in comment.replies"
        :key="reply.comment_id"
        :comment="reply"
        :depth="depth + 1"
        :current-user-id="currentUserId"
        @reply="$emit('reply', $event)"
        @delete="$emit('delete', $event)"
        @refresh="$emit('refresh')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { getAvatarUrl } from '@/services/ApiServices'
import type { ForumComment } from '@/interfaces/types'

const props = defineProps<{
  comment: ForumComment
  depth: number
  currentUserId?: number
}>()

const emit = defineEmits<{
  reply: [commentId: number]
  delete: [commentId: number]
  refresh: []
}>()

const formatTime = (dateString: string) => {
  if (!dateString) return '未知'
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days} 天前`
  if (hours > 0) return `${hours} 小时前`
  const minutes = Math.floor(diff / (1000 * 60))
  if (minutes > 0) return `${minutes} 分钟前`
  return '刚刚'
}

const handleReply = () => {
  emit('reply', props.comment.comment_id)
}

const handleDelete = () => {
  emit('delete', props.comment.comment_id)
}

const isCommentAuthor = () => {
  return props.currentUserId && props.currentUserId === props.comment.author_id
}
</script>

<style scoped>
.comment-item {
  padding: 16px;
  border-radius: 10px;
  background: #f8f9fa;
  transition: background 0.2s;
}

.comment-item:hover {
  background: #f1f3f5;
}

.comment-item.floor {
  border-left: 4px solid #ea6685;
}

.comment-item.reply {
  margin-left: 40px;
  border-left: 3px solid #e9ecef;
  font-size: 14px;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
}

.comment-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.author {
  font-weight: 600;
  color: #333;
}

.floor-number {
  padding: 2px 8px;
  background: #667eea;
  color: white;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.time {
  font-size: 13px;
  color: #999;
}

.comment-content {
  color: #333;
  line-height: 1.6;
  margin-bottom: 12px;
  white-space: pre-wrap;
}

.comment-actions {
  display: flex;
  gap: 10px;
}

.btn-reply {
  padding: 6px 16px;
  background: transparent;
  color: #667eea;
  border: 1px solid #667eea;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-reply:hover {
  background: #667eea;
  color: white;
}

.btn-delete {
  padding: 6px 10px;
  background: transparent;
  color: #e74c3c;
  border: 1px solid #e74c3c;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-delete:hover {
  background: #e74c3c;
  color: white;
}

.replies {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
  padding-left: 10px;
  border-left: 2px dashed #e9ecef;
}

@media (max-width: 600px) {
  .comment-item.reply {
    margin-left: 20px;
  }
}
</style>
