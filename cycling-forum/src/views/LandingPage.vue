<script setup lang="ts">
import { useRouter } from 'vue-router'
import apiService, { fetchPlatformStats, fetchForumPosts, fetchRiders } from '@/services/ApiServices'
import { ref, onMounted } from 'vue'
import type { User, ForumPost, Rider } from '@/interfaces/types'

const router = useRouter()
const currentUser = ref<User | null>(null)

// 统计数据
const stats = ref({
  rider_count: 0,
  user_count: 0,
  post_count: 0,
  rating_count: 0
})
const isLoadingStats = ref(false)

// 热门讨论（最新5条帖子）
const hotPosts = ref<ForumPost[]>([])
const isLoadingPosts = ref(false)

// 明星车手（Top 5评分）
const topRiders = ref<Rider[]>([])
const isLoadingRiders = ref(false)

onMounted(async () => {
  const userStr = localStorage.getItem('user')
  if (userStr) {
    currentUser.value = JSON.parse(userStr)
  }

  // 加载统计数据
  loadStats()

  // 加载热门讨论
  loadHotPosts()

  // 加载明星车手
  loadTopRiders()
})

const loadStats = async () => {
  isLoadingStats.value = true
  try {
    stats.value = await fetchPlatformStats()
  } catch (error) {
    console.error('加载统计数据失败:', error)
  } finally {
    isLoadingStats.value = false
  }
}

const loadHotPosts = async () => {
  isLoadingPosts.value = true
  try {
    const response = await fetchForumPosts(1, 5, 'created_at', 'desc')
    hotPosts.value = response.data
  } catch (error) {
    console.error('加载热门讨论失败:', error)
  } finally {
    isLoadingPosts.value = false
  }
}

const loadTopRiders = async () => {
  isLoadingRiders.value = true
  try {
    const response = await fetchRiders(1, 5, undefined, 'rating_score')
    topRiders.value = response.data
  } catch (error) {
    console.error('加载明星车手失败:', error)
  } finally {
    isLoadingRiders.value = false
  }
}

const navigateToRaces = () => {
  router.push('/races')
}

const navigateToRiders = () => {
  router.push('/riders')
}

const navigateToForum = () => {
  router.push('/forum')
}

const navigateToPost = (postId: number) => {
  router.push(`/forum/post/${postId}`)
}

const navigateToRider = (riderId: number) => {
  router.push(`/riders/${riderId}`)
}

const navigateToLogin = () => {
  router.push('/login')
}

const navigateToProfile = () => {
  router.push('/profile')
}

const handleLogout = () => {
  apiService.logout()
  currentUser.value = null
  router.push('/')
}
</script>

<template>
  <div class="landing-container">
    <!-- 顶部用户栏 -->
    <div class="user-bar">
      <div v-if="currentUser" class="user-info" @click="navigateToProfile">
        <span>欢迎, {{ currentUser.nickname }}</span>
        <button @click.stop="handleLogout" class="btn-logout-small">退出</button>
      </div>
      <div v-else class="auth-links">
        <button @click="navigateToLogin" class="btn-login-small">登录</button>
        <button @click="() => router.push('/register')" class="btn-register-small">注册</button>
      </div>
    </div>

    <div class="hero-section">
      <h1 class="hero-title">环法自行车赛交流站</h1>
      <p class="hero-subtitle">探索百年赛事历史，追踪传奇车手足迹</p>
    </div>

    <!-- 数据统计仪表板 -->
    <div v-if="!isLoadingStats" class="stats-dashboard">
      <div class="stat-item">
        <div class="stat-icon">🚴</div>
        <div class="stat-info">
          <div class="stat-number">{{ stats.rider_count }}</div>
          <div class="stat-label">位车手</div>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon">📝</div>
        <div class="stat-info">
          <div class="stat-number">{{ stats.post_count }}</div>
          <div class="stat-label">篇帖子</div>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon">⭐</div>
        <div class="stat-info">
          <div class="stat-number">{{ stats.rating_count }}</div>
          <div class="stat-label">条评价</div>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon">👥</div>
        <div class="stat-info">
          <div class="stat-number">{{ stats.user_count }}</div>
          <div class="stat-label">位用户</div>
        </div>
      </div>
    </div>
    <div v-else class="stats-dashboard">
      <div class="stat-item loading">加载统计中...</div>
    </div>

    <div class="cards-container">
      <!-- 赛事入口卡片 -->
      <div class="entry-card race-card" @click="navigateToRaces">
        <div class="card-icon">🏆</div>
        <h2 class="card-title">赛事数据</h2>
        <p class="card-description">浏览历届环法赛事，查看每个赛段的详细成绩与排名</p>
        <div class="card-arrow">→</div>
      </div>

      <!-- 车手入口卡片 -->
      <div class="entry-card rider-card" @click="navigateToRiders">
        <div class="card-icon">🚴</div>
        <h2 class="card-title">车手信息</h2>
        <p class="card-description">搜索车手资料，查看参赛记录、冠军数量与效力车队</p>
        <div class="card-arrow">→</div>
      </div>

      <!-- 论坛入口卡片 -->
      <div class="entry-card forum-card" @click="navigateToForum">
        <div class="card-icon">🗣️</div>
        <h2 class="card-title">论坛</h2>
        <p class="card-description">参与讨论，分享观点，连接环法自行车赛爱好者社区</p>
        <div class="card-arrow">→</div>
      </div>
    </div>

    <!-- 热门内容区域 -->
    <div class="content-sections">
      <!-- 热门讨论 -->
      <div class="content-section">
        <div class="section-header">
          <h3 class="section-title">🔥 热门讨论</h3>
          <button @click="navigateToForum" class="btn-view-all">查看全部 →</button>
        </div>
        <div v-if="isLoadingPosts" class="section-loading">加载中...</div>
        <div v-else-if="hotPosts.length === 0" class="section-empty">暂无帖子</div>
        <div v-else class="post-list">
          <div
            v-for="post in hotPosts"
            :key="post.post_id"
            class="post-item"
            @click="navigateToPost(post.post_id)"
          >
            <h4 class="post-title">{{ post.title }}</h4>
            <div class="post-meta">
              <span class="post-author">{{ post.author_nickname || '匿名' }}</span>
              <span class="post-stats">👁 {{ post.view_count }} 💬 {{ post.comment_count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 明星车手 -->
      <div class="content-section">
        <div class="section-header">
          <h3 class="section-title">⭐ 明星车手</h3>
          <button @click="navigateToRiders" class="btn-view-all">查看全部 →</button>
        </div>
        <div v-if="isLoadingRiders" class="section-loading">加载中...</div>
        <div v-else-if="topRiders.length === 0" class="section-empty">暂无评分</div>
        <div v-else class="rider-list">
          <div
            v-for="rider in topRiders"
            :key="rider.rider_id"
            class="rider-item"
            @click="navigateToRider(rider.rider_id)"
          >
            <div class="rider-avatar">{{ rider.rider_name.charAt(0) }}</div>
            <div class="rider-info">
              <h4 class="rider-name">{{ rider.rider_name }}</h4>
              <div class="rider-rating">
                ⭐ {{ rider.avg_rating?.toFixed(1) || '0.0' }}
                <span class="rating-count">({{ rider.rating_count || 0 }}人评价)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <footer class="landing-footer">
      <p>Tour de France Database © 2025</p>
    </footer>
  </div>
</template>

<style scoped>
.landing-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  position: relative;
  overflow: hidden;
  padding-bottom: 3rem;
}

/* 背景层：三个倾斜的颜色区域 */
.landing-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    135deg,
    #ff286e 0%,
    #ff286e 35%,
    #ffed00 35%,
    #ffed00 65%,
    #da291c 65%,
    #da291c 100%
  );
  z-index: 0;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
}

.landing-container::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.1) 25%,
    transparent 25%,
    transparent 50%,
    rgba(255, 255, 255, 0.1) 50%,
    rgba(255, 255, 255, 0.1) 75%,
    transparent 75%,
    transparent 100%
  );
  background-size: 60px 60px;
  background-blend-mode: multiply;
  clip-path: polygon(25% 0%, 100% 0%, 75% 100%, 0% 100%);
  z-index: 1;
}

.landing-container {
  background-color: rgba(48, 47, 47, 0.968);
}

.hero-section {
  text-align: center;
  margin-bottom: 3rem;
  animation: fadeInDown 0.8s ease-out;
  position: relative;
  z-index: 10;
  text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.3);
  margin-top: 2rem;
}

.hero-title {
  font-size: 3.5rem;
  font-weight: 800;
  color: white;
  margin-bottom: 1rem;
  text-shadow: 3px 3px 12px rgba(0, 0, 0, 0.4);
  letter-spacing: -0.02em;
}

.hero-subtitle {
  font-size: 1.25rem;
  color: rgba(255, 255, 255, 0.95);
  font-weight: 300;
  text-shadow: 2px 2px 6px rgba(0, 0, 0, 0.3);
}

/* 数据统计仪表板 */
.stats-dashboard {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 3rem;
  position: relative;
  z-index: 10;
  animation: fadeInUp 0.8s ease-out;
}

.stat-item {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  padding: 1.5rem 2rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
  min-width: 140px;
}

.stat-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
}

.stat-icon {
  font-size: 2.5rem;
}

.stat-number {
  font-size: 2rem;
  font-weight: 800;
  color: #1e293b;
  line-height: 1;
}

.stat-label {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 600;
  margin-top: 0.25rem;
}

.cards-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  max-width: 1200px;
  width: 100%;
  animation: fadeInUp 1s ease-out;
  position: relative;
  z-index: 10;
  margin-bottom: 3rem;
}

.entry-card {
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  padding: 2.5rem 2rem;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.entry-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #fbbf24, #f59e0b);
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.entry-card:hover::before {
  transform: scaleX(1);
}

.entry-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3);
}

.card-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  filter: grayscale(0.3);
  transition: all 0.3s ease;
}

.entry-card:hover .card-icon {
  filter: grayscale(0);
  transform: scale(1.1);
}

.card-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.75rem;
}

.card-description {
  font-size: 1rem;
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 1.5rem;
}

.card-arrow {
  font-size: 1.5rem;
  color: #f59e0b;
  font-weight: 700;
  text-align: right;
  transition: transform 0.3s ease;
}

.entry-card:hover .card-arrow {
  transform: translateX(8px);
}

/* 热门内容区域 */
.content-sections {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  max-width: 1200px;
  width: 100%;
  position: relative;
  z-index: 10;
  animation: fadeInUp 1.2s ease-out;
}

.content-section {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  padding: 2rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #f0f0f0;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.btn-view-all {
  padding: 6px 12px;
  background: transparent;
  color: #ff286e;
  border: 1px solid #ff286e;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-view-all:hover {
  background: #ff286e;
  color: white;
}

.section-loading,
.section-empty {
  text-align: center;
  padding: 2rem;
  color: #94a3b8;
}

/* 热门讨论列表 */
.post-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.post-item {
  padding: 1rem;
  background: #f8fafc;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid #e2e8f0;
}

.post-item:hover {
  background: #eff6ff;
  border-color: #3b82f6;
  transform: translateX(4px);
}

.post-title {
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 0.5rem 0;
  line-height: 1.4;
}

.post-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
  color: #64748b;
}

.post-author {
  font-weight: 600;
  color: #ff286e;
}

.post-stats {
  font-size: 0.8125rem;
}

/* 明星车手列表 */
.rider-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.rider-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid #e2e8f0;
}

.rider-item:hover {
  background: #eff6ff;
  border-color: #3b82f6;
  transform: translateX(4px);
}

.rider-avatar {
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: white;
  font-size: 1.5rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
}

.rider-info {
  flex: 1;
}

.rider-name {
  font-size: 1rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 0.25rem 0;
}

.rider-rating {
  font-size: 0.9rem;
  color: #f59e0b;
  font-weight: 600;
}

.rating-count {
  font-size: 0.75rem;
  color: #94a3b8;
  font-weight: 400;
  margin-left: 0.5rem;
}

.landing-footer {
  margin-top: 3rem;
  color: black;
  font-size: 0.875rem;
  position: relative;
  z-index: 10;
  font-weight: 500;
  text-shadow: 1px 1px 4px rgba(230, 228, 228, 0.3);
}

/* 用户栏样式 */
.user-bar {
  position: fixed;
  top: 0;
  right: 0;
  padding: 15px 30px;
  z-index: 1000;
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

.auth-links {
  display: flex;
  gap: 10px;
}

.btn-logout-small,
.btn-login-small,
.btn-register-small {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-logout-small {
  background: rgba(231, 76, 60, 0.9);
  color: white;
}

.btn-logout-small:hover {
  background: rgba(192, 57, 43, 1);
}

.btn-login-small {
  background: rgba(255, 255, 255, 0.9);
  color: #667eea;
}

.btn-login-small:hover {
  background: white;
}

.btn-register-small {
  background: rgba(102, 126, 234, 0.9);
  color: white;
}

.btn-register-small:hover {
  background: rgba(102, 126, 234, 1);
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1024px) {
  .content-sections {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2.5rem;
  }

  .cards-container {
    grid-template-columns: 1fr;
    max-width: 400px;
  }

  .stats-dashboard {
    flex-wrap: wrap;
    justify-content: center;
  }

  .stat-item {
    min-width: 120px;
    padding: 1rem 1.5rem;
  }

  .user-bar {
    padding: 10px 15px;
  }

  .btn-logout-small,
  .btn-login-small,
  .btn-register-small {
    padding: 6px 12px;
    font-size: 14px;
  }
}
</style>
