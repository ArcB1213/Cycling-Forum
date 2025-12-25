<template>
  <div class="info-card">
    <div class="avatar-section">
      <div
        class="avatar-wrapper"
        @click="handleAvatarClick"
        title="点击查看大图"
        :class="{ 'avatar-cursor': isOwner }"
      >
        <img :src="getAvatarUrl()" alt="用户头像" class="user-avatar" />
        <div v-if="isOwner" class="avatar-overlay">
          <span>查看大图</span>
        </div>
      </div>
      <div class="user-details">
        <div v-if="isOwner" style="display: flex; align-items: center; gap: 10px">
          <h2>{{ user?.nickname }}</h2>
          <button @click="$emit('edit-nickname')" class="btn-edit">修改</button>
        </div>
        <h2 v-else>{{ user?.nickname }}</h2>

        <p v-if="isOwner" class="user-email">{{ user?.email }}</p>
        <p class="user-date">注册时间: {{ formatDate(user?.created_at) }}</p>
        <span v-if="user?.is_verified" class="badge-verified">✓ 已验证</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { User } from '@/interfaces/types'
import { getAvatarUrl as apiGetAvatarUrl } from '@/services/ApiServices'

interface Props {
  user: User | null
  isOwner: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'edit-nickname': []
  'edit-avatar': []
}>()

const getAvatarUrl = () => {
  return apiGetAvatarUrl(props.user?.avatar)
}

const handleAvatarClick = () => {
  if (props.isOwner) {
    emit('edit-avatar')
  }
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}
</script>

<style scoped>
.info-card {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.avatar-section {
  display: flex;
  align-items: center;
  gap: 25px;
}

.avatar-wrapper {
  position: relative;
  border-radius: 50%;
  overflow: hidden;
  width: 200px;
  height: 200px;
  border: 4px solid #ff286e;
  transition: transform 0.3s;
}

.avatar-cursor {
  cursor: pointer;
}

.avatar-cursor:hover {
  transform: scale(1.05);
}

.avatar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
}

.avatar-cursor:hover .avatar-overlay {
  opacity: 1;
}

.avatar-overlay span {
  color: white;
  font-size: 14px;
  font-weight: 600;
}

.user-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-details h2 {
  font-size: 24px;
  font-weight: 700;
  color: #333;
  margin: 0 0 8px 0;
}

.user-email {
  font-size: 15px;
  color: #666;
  margin: 0 0 4px 0;
}

.user-date {
  font-size: 13px;
  color: #999;
  margin: 0 0 8px 0;
}

.badge-verified {
  display: inline-block;
  padding: 4px 10px;
  background: #27ae60;
  color: white;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.btn-edit {
  padding: 4px 12px;
  background: #f0f0f0;
  color: #333;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-edit:hover {
  background: #da291c;
  color: white;
}

@media (max-width: 768px) {
  .avatar-section {
    flex-direction: column;
    text-align: center;
  }
}
</style>
