<template>
  <div class="forum-container">
    <div class="forum-header">
      <h1>🏁 自行车论坛</h1>
      <div class="user-info" @click="navigateToProfile">
        <span>欢迎, {{ user?.nickname }}</span>
        <button @click.stop="handleLogout" class="btn-logout">退出登录</button>
      </div>
    </div>

    <div v-if="isLoading" class="loading">加载中...</div>

    <div v-else-if="error" class="error-box">
      {{ error }}
    </div>

    <div v-else class="forum-content">
      <div class="forum-welcome">
        <h2>{{ forumData?.message }}</h2>
        <div class="user-card">
          <img :src="apiService.getAvatarUrl(user?.avatar)" alt="头像" class="avatar" />
          <div class="user-details">
            <p><strong>用户 ID:</strong> {{ user?.user_id }}</p>
            <p><strong>邮箱:</strong> {{ user?.email }}</p>
            <p><strong>昵称:</strong> {{ user?.nickname }}</p>
            <p><strong>注册时间:</strong> {{ formatDate(user?.created_at) }}</p>
          </div>
        </div>
      </div>

      <div class="posts-section">
        <h3>📝 论坛帖子列表</h3>
        <div class="posts-list">
          <div v-for="post in forumData?.posts" :key="post.id" class="post-card">
            <h4>{{ post.title }}</h4>
            <p class="post-author">作者: {{ post.author }}</p>
            <p class="post-content">{{ post.content }}</p>
          </div>
        </div>
      </div>

      <div class="back-home">
        <router-link to="/" class="btn-home">返回首页</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import apiService from '@/services/ApiServices'
import type { User, ForumPost } from '@/interfaces/types'

const router = useRouter()
const isLoading = ref(false)
const error = ref('')
const user = ref<User | null>(null)

interface ForumData {
  message: string
  user: User
  posts: ForumPost[]
}

const forumData = ref<ForumData | null>(null)

const formatDate = (dateString?: string) => {
  if (!dateString) return '未知'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

const loadForumData = async () => {
  isLoading.value = true
  error.value = ''

  try {
    const response = await apiService.getForumPosts()
    forumData.value = response
    user.value = response.user
  } catch (err: unknown) {
    console.error('加载论坛数据失败:', err)
    const error_obj = err as { response?: { status?: number; data?: { detail?: string } } }
    error.value = error_obj.response?.data?.detail || '加载失败，请重新登录'

    // 如果是 401 错误，跳转到登录页
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

const handleLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
  router.push('/login')
}

const navigateToProfile = () => {
  router.push('/profile')
}

onMounted(() => {
  // 从 localStorage 获取用户信息
  const storedUser = localStorage.getItem('user')
  if (storedUser) {
    user.value = JSON.parse(storedUser)
  }

  loadForumData()
})
</script>

<style scoped>
.forum-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 40px 20px;
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.forum-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 20px 30px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  margin-bottom: 30px;
}

.forum-header h1 {
  font-size: 32px;
  color: #333;
  margin: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
  color: white;
  font-weight: 600;
  text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  transition: opacity 0.3s;
}

.user-info span {
  color: black;
  font-weight: bold;
  border: #ff286e 2px solid;
  padding: 4px 8px;
  border-radius: 4px;
}

.user-info span:hover {
  background-color: #ff286e;
  color: white;
}

.btn-logout {
  padding: 8px 20px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.3s;
}

.btn-logout:hover {
  background: #c0392b;
}

.loading,
.error-box {
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.error-box {
  color: #e74c3c;
  font-weight: 600;
}

.forum-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.forum-welcome {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.forum-welcome h2 {
  font-size: 24px;
  color: #ff286e;
  margin-bottom: 20px;
}

.user-card {
  display: flex;
  gap: 20px;
  align-items: center;
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-top: 15px;
}

.avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid #ffed00;
}

.user-details {
  flex: 1;
}

.user-details p {
  margin: 8px 0;
  color: #555;
  font-size: 15px;
}

.posts-section {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.posts-section h3 {
  font-size: 22px;
  color: #333;
  margin-bottom: 20px;
}

.posts-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.post-card {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border-left: 4px solid #ffed00;
  transition: transform 0.2s;
}

.post-card:hover {
  transform: translateX(5px);
}

.post-card h4 {
  font-size: 18px;
  color: #333;
  margin: 0 0 10px 0;
}

.post-author {
  font-size: 14px;
  color: #888;
  margin: 5px 0;
}

.post-content {
  font-size: 15px;
  color: #555;
  margin: 10px 0 0 0;
}

.back-home {
  text-align: center;
}

.btn-home {
  display: inline-block;
  padding: 12px 30px;
  background: white;
  color: #da291c;
  text-decoration: none;
  border-radius: 6px;
  font-weight: 600;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.btn-home:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
  background: #da291c;
  color: white;
}
</style>
