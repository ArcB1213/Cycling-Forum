<template>
  <div class="forum-container">
    <div class="forum-header">
      <h1>🏁 自行车论坛</h1>
      <div class="header-actions">
        <button @click="goToMain" class="btn-back-forum">返回首页</button>
        <button @click="goToCreatePost" class="btn-create">+ 发帖</button>
        <div class="user-info" @click="navigateToProfile">
          <span>{{ user?.nickname }}</span>
          <button @click.stop="handleLogout" class="btn-logout">退出</button>
        </div>
      </div>
    </div>

    <div v-if="isLoading && !posts.length" class="loading">加载中...</div>

    <div v-else-if="error" class="error-box">
      {{ error }}
    </div>

    <div v-else class="forum-content">
      <!-- 排序控制器 -->
      <div class="sort-controls">
        <label class="sort-label">排序方式：</label>
        <select v-model="sortBy" @change="onSortChange" class="sort-select">
          <option value="created_at">发布时间</option>
          <option value="comment_count">评论数</option>
          <option value="view_count">浏览量</option>
        </select>
        <select v-model="order" @change="onSortChange" class="sort-select">
          <option value="desc">降序</option>
          <option value="asc">升序</option>
        </select>
      </div>

      <!-- 帖子列表 -->
      <div class="content-card posts-section">
        <div v-if="posts.length === 0" class="empty-state">
          <p>还没有帖子，快来发布第一条吧！</p>
          <button @click="goToCreatePost" class="btn-create-large">发布新帖</button>
        </div>

        <div v-else class="posts-list">
          <div
            v-for="post in posts"
            :key="post.post_id"
            class="post-card"
            @click="goToPostDetail(post.post_id)"
          >
            <div class="post-header">
              <h3 class="post-title">{{ post.title }}</h3>
              <span class="post-meta">{{ formatDate(post.created_at) }}</span>
            </div>
            <p class="post-content">{{ truncateContent(post.content) }}</p>
            <div class="post-footer">
              <div class="post-author" @click.stop="goToUserProfile(post.author_id)">
                <img :src="getAvatarUrl(post.author_avatar)" class="author-avatar" />
                <span>{{ post.author_nickname || '未知用户' }}</span>
              </div>
              <div class="post-stats">
                <span class="stat">👁 {{ post.view_count }}</span>
                <span class="stat">💬 {{ post.comment_count }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="pagination.total_pages > 1" class="pagination">
          <button
            :disabled="!pagination.has_prev"
            @click="changePage(pagination.page - 1)"
            class="btn-page"
          >
            上一页
          </button>
          <span class="page-info">第 {{ pagination.page }} / {{ pagination.total_pages }} 页</span>
          <button
            :disabled="!pagination.has_next"
            @click="changePage(pagination.page + 1)"
            class="btn-page"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import '@/assets/forum-styles.css'
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import apiService, { getAvatarUrl, fetchForumPosts } from '@/services/ApiServices'
import type { ForumPost, PaginationMeta } from '@/interfaces/types'

const router = useRouter()
const route = useRoute()
const isLoading = ref(false)
const error = ref('')
const user = ref<User | null>(null)
const posts = ref<ForumPost[]>([])
const pagination = ref<PaginationMeta>({
  total: 0,
  page: 1,
  limit: 20,
  total_pages: 0,
  has_next: false,
  has_prev: false,
})

// 排序状态
const sortBy = ref<'created_at' | 'comment_count' | 'view_count'>('created_at')
const order = ref<'asc' | 'desc'>('desc')

const formatDate = (dateString: string) => {
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

const truncateContent = (content: string, maxLength = 150) => {
  if (!content) return ''
  if (content.length <= maxLength) return content
  return content.substring(0, maxLength) + '...'
}

const loadPosts = async (page: number = 1) => {
  isLoading.value = true
  error.value = ''

  try {
    const response = await fetchForumPosts(page, 10, sortBy.value, order.value)
    posts.value = response.data
    pagination.value = response.pagination
  } catch (err: unknown) {
    console.error('加载帖子失败:', err)
    const error_obj = err as { response?: { status?: number; data?: { detail?: string } } }
    error.value = error_obj.response?.data?.detail || '加载失败，请重新登录'

    if (error_obj.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      router.push('/login')
    }
  } finally {
    isLoading.value = false
  }
}

// 当排序方式改变时重新加载帖子
const onSortChange = () => {
  loadPosts(1) // 重置到第一页
}

const changePage = (page: number) => {
  if (page >= 1 && page <= pagination.value.total_pages) {
    loadPosts(page)
    // 滚动到顶部
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

const handleLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
  router.push('/login')
}

const navigateToProfile = () => {
  router.push('/profile')
}

const goToCreatePost = () => {
  router.push('/forum/create')
}

const goToPostDetail = (postId: number) => {
  router.push(`/forum/post/${postId}`)
}

const goToMain = () => {
  router.push('/')
}

const goToUserProfile = (authorId: number) => {
  const currentUser = JSON.parse(localStorage.getItem('user') || '{}')
  // 确保 user_id 是数字类型再比较
  const currentUserId = Number(currentUser.user_id)

  if (currentUserId === authorId) {
    router.push('/profile')
  } else {
    router.push(`/profile/${authorId}`)
  }
}

onMounted(() => {
  const storedUser = localStorage.getItem('user')
  if (storedUser) {
    user.value = JSON.parse(storedUser)
  }

  loadPosts()
})

// 监听路由变化，当从其他页面返回时自动刷新帖子列表
watch(
  () => route.path,
  (newPath) => {
    // 只在进入论坛页面时刷新
    if (newPath === '/forum') {
      loadPosts()
    }
  }
)
</script>

<style scoped>
/* 排序控制器样式 */
.sort-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: white;
  border-radius: 10px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.sort-label {
  font-weight: 600;
  color: #333;
  font-size: 15px;
}

.sort-select {
  padding: 8px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.sort-select:hover {
  border-color: #ffed00;
}

.sort-select:focus {
  outline: none;
  border-color: #ffed00;
  box-shadow: 0 0 0 3px rgba(255, 237, 0, 0.1);
}

/* 帖子列表特定样式 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-state p {
  font-size: 18px;
  color: #888;
  margin-bottom: 20px;
}

.btn-create-large {
  padding: 14px 32px;
  background: #ffed00;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 16px;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.btn-create-large:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.posts-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.post-card {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
  border-left: 4px solid #ffed00;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
  cursor: pointer;
}

.post-card:hover {
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.post-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.post-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.post-meta {
  font-size: 13px;
  color: #999;
}

.post-content {
  color: #555;
  line-height: 1.6;
  margin: 12px 0;
}

.post-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 15px;
}

.post-author {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.post-author:hover {
  opacity: 0.7;
}

.author-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
}

.post-stats {
  display: flex;
  gap: 15px;
}

.stat {
  font-size: 14px;
  color: #888;
}
</style>
