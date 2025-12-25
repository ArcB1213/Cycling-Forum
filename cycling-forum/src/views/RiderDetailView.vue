<script setup lang="ts">
import '@/assets/forum-styles.css'
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type {
  ApiRiderDetail,
  ApiRiderRaces,
  ApiRiderWins,
  RiderDetailWithRatings,
  RatingCreate,
  PaginatedRatingsResponse,
  PaginatedGCResponse,
  User,
} from '@/interfaces/types'
import {
  fetchRiderDetail,
  fetchRiderRaces,
  fetchRiderWins,
  fetchRiderDetailWithRatings,
  submitRating,
  fetchRiderRatings,
  deleteRating,
  isAuthenticated,
  logout,
  fetchRiderGCHistory,
} from '@/services/ApiServices'

const router = useRouter()
const route = useRoute()
const currentUser = ref<User | null>(null)

const riderDetail = ref<ApiRiderDetail | null>(null)
const riderRaces = ref<ApiRiderRaces | null>(null)
const riderWins = ref<ApiRiderWins | null>(null)
const riderRatings = ref<RiderDetailWithRatings | null>(null)
const ratingsList = ref<PaginatedRatingsResponse | null>(null)
const riderGCHistory = ref<PaginatedGCResponse | null>(null)

const isLoading = ref<boolean>(false)
const isLoadingRaces = ref<boolean>(false)
const isLoadingWins = ref<boolean>(false)
const isLoadingRatings = ref<boolean>(false)
const isLoadingGCHistory = ref<boolean>(false)
const isSubmittingRating = ref<boolean>(false)
const error = ref<string | null>(null)

// 评分表单
const userScore = ref<number>(0)
const userComment = ref<string>('')
const showRatingForm = ref<boolean>(false)

// 当前激活的标签页: 'races' | 'wins' | 'teams' | 'ratings' | 'gc'
const activeTab = ref<'races' | 'wins' | 'teams' | 'ratings' | 'gc'>('teams')

// 参赛记录分页
const racesCurrentPage = ref<number>(1)
const gcHistoryCurrentPage = ref<number>(1)

const isLoggedIn = computed(() => isAuthenticated())

const loadRiderDetail = async () => {
  const riderId = Number(route.params.id)
  if (isNaN(riderId)) {
    error.value = '无效的车手 ID'
    return
  }

  isLoading.value = true
  error.value = null
  try {
    // 并行加载基本详情和评分详情
    const [detail, ratings] = await Promise.all([
      fetchRiderDetail(riderId),
      fetchRiderDetailWithRatings(riderId),
    ])
    riderDetail.value = detail
    riderRatings.value = ratings

    // 如果用户已评分，初始化表单
    if (ratings.user_rating) {
      userScore.value = ratings.user_rating.score
      userComment.value = ratings.user_rating.comment || ''
    }
  } catch (err) {
    console.error(err)
    error.value = '无法加载车手详情，请检查后端服务'
  } finally {
    isLoading.value = false
  }
}

const loadRatingsList = async (page = 1) => {
  const riderId = Number(route.params.id)
  isLoadingRatings.value = true
  try {
    ratingsList.value = await fetchRiderRatings(riderId, page)
  } catch (err) {
    console.error(err)
  } finally {
    isLoadingRatings.value = false
  }
}

const handleRatingSubmit = async () => {
  if (userScore.value === 0) {
    alert('请选择评分星级')
    return
  }

  const riderId = Number(route.params.id)
  isSubmittingRating.value = true
  try {
    const ratingData: RatingCreate = {
      rider_id: riderId,
      score: userScore.value,
      comment: userComment.value,
    }
    await submitRating(riderId, ratingData)

    // 重新加载评分数据
    const ratings = await fetchRiderDetailWithRatings(riderId)
    riderRatings.value = ratings
    showRatingForm.value = false

    // 如果当前在评价列表页，刷新列表
    if (activeTab.value === 'ratings') {
      await loadRatingsList()
    }

    alert('评价提交成功！')
  } catch (err) {
    console.error(err)
    alert('评价提交失败，请稍后重试')
  } finally {
    isSubmittingRating.value = false
  }
}

const handleRatingDelete = async () => {
  if (!confirm('确定要删除您的评价吗？此操作不可恢复。')) {
    return
  }

  const riderId = Number(route.params.id)
  isSubmittingRating.value = true
  try {
    await deleteRating(riderId)

    // 重置表单
    userScore.value = 0
    userComment.value = ''
    showRatingForm.value = false

    // 重新加载评分数据
    const ratings = await fetchRiderDetailWithRatings(riderId)
    riderRatings.value = ratings

    // 如果当前在评价列表页，刷新列表
    if (activeTab.value === 'ratings') {
      await loadRatingsList()
    }

    alert('评价已删除')
  } catch (err) {
    console.error(err)
    alert('删除评价失败，请稍后重试')
  } finally {
    isSubmittingRating.value = false
  }
}

const goBack = () => {
  router.push('/riders')
}

const navigateToProfile = () => {
  router.push('/profile')
}

const handleLogout = () => {
  logout()
  currentUser.value = null
  router.push('/')
}

const setActiveTab = async (tab: 'races' | 'wins' | 'teams' | 'ratings' | 'gc') => {
  activeTab.value = tab

  const riderId = Number(route.params.id)

  // 根据选择的标签页加载对应数据（如果还没加载过）
  if (tab === 'races' && !riderRaces.value) {
    isLoadingRaces.value = true
    try {
      riderRaces.value = await fetchRiderRaces(riderId, 1, 20)
      racesCurrentPage.value = 1
    } catch (err) {
      console.error(err)
      error.value = '加载参赛记录失败'
    } finally {
      isLoadingRaces.value = false
    }
  } else if (tab === 'wins' && !riderWins.value) {
    isLoadingWins.value = true
    try {
      riderWins.value = await fetchRiderWins(riderId)
    } catch (err) {
      console.error(err)
      error.value = '加载冠军记录失败'
    } finally {
      isLoadingWins.value = false
    }
  } else if (tab === 'ratings' && !ratingsList.value) {
    await loadRatingsList()
  } else if (tab === 'gc' && !riderGCHistory.value) {
    await loadGCHistoryPage(1)
  }
}

const loadGCHistoryPage = async (page: number) => {
  const riderId = Number(route.params.id)
  isLoadingGCHistory.value = true
  try {
    riderGCHistory.value = await fetchRiderGCHistory(riderId, page, 20)
    gcHistoryCurrentPage.value = page
  } catch (err) {
    console.error(err)
    error.value = '加载总成绩记录失败'
  } finally {
    isLoadingGCHistory.value = false
  }
}

const formatTime = (totalSeconds: number): string => {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  const pad = (num: number) => num.toString().padStart(2, '0')
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`
}

const formatStageName = (stageNumber: number): string => {
  return stageNumber === 0 ? 'Prologue' : `Stage ${stageNumber}`
}

// 加载参赛记录指定页
const loadRacesPage = async (page: number) => {
  const riderId = Number(route.params.id)
  isLoadingRaces.value = true
  try {
    riderRaces.value = await fetchRiderRaces(riderId, page, 20)
    racesCurrentPage.value = page
  } catch (err) {
    console.error(err)
    error.value = '加载参赛记录失败'
  } finally {
    isLoadingRaces.value = false
  }
}

const formatDate = (dateStr: string): string => {
  return new Date(dateStr).toLocaleDateString()
}

onMounted(() => {
  // 加载当前用户信息
  const userStr = localStorage.getItem('user')
  if (userStr) {
    currentUser.value = JSON.parse(userStr)
  }

  loadRiderDetail()
})
</script>

<template>
  <div class="page-container rider-detail-page">
    <!-- 顶部用户栏 -->
    <div class="user-bar">
      <div v-if="currentUser" class="user-info" @click="navigateToProfile">
        <span>欢迎, {{ currentUser.nickname }}</span>
        <button @click.stop="handleLogout" class="btn-logout-small">退出</button>
      </div>
      <div v-else class="auth-links">
        <button @click="() => router.push('/login')" class="btn-login-small">登录</button>
        <button @click="() => router.push('/register')" class="btn-register-small">注册</button>
      </div>
    </div>

    <!-- 顶部导航 -->
    <header class="page-header">
      <button class="back-button" @click="goBack">← 返回车手列表</button>
    </header>

    <!-- 加载与错误状态 -->
    <div v-if="error" class="status-message error-message">{{ error }}</div>
    <div v-if="isLoading" class="status-message loading-message">加载车手数据中...</div>

    <!-- 车手详情 -->
    <div v-else-if="riderDetail" class="rider-detail">
      <!-- 车手基本信息卡片 -->
      <div class="info-card main-card">
        <div class="rider-avatar-large">
          {{ riderDetail.rider.rider_name.charAt(0) }}
        </div>
        <h1 class="rider-name-large">{{ riderDetail.rider.rider_name }}</h1>
        <p class="rider-id-badge">ID: {{ riderDetail.rider.rider_id }}</p>
      </div>

      <!-- 统计数据卡片组 -->
      <div class="stats-grid">
        <div
          class="stat-card"
          :class="{ active: activeTab === 'races' }"
          @click="setActiveTab('races')"
          role="button"
          tabindex="0"
        >
          <div class="stat-icon">🏁</div>
          <div class="stat-value">{{ riderDetail.stats.total_races }}</div>
          <div class="stat-label">参赛场次</div>
        </div>

        <div
          class="stat-card"
          :class="{ active: activeTab === 'gc' }"
          @click="setActiveTab('gc')"
          role="button"
          tabindex="0"
        >
          <div class="stat-icon">📊</div>
          <div class="stat-value">{{ riderDetail.stats.total_gc_entries || 0 }}</div>
          <div class="stat-label">总成绩排名历史</div>
        </div>

        <div
          class="stat-card highlight-card"
          :class="{ active: activeTab === 'wins' }"
          @click="setActiveTab('wins')"
          role="button"
          tabindex="0"
        >
          <div class="stat-icon">🏆</div>
          <div class="stat-value">
            {{ riderDetail.stats.stage_wins }} | {{ riderDetail.stats.gc_wins }}
          </div>
          <div class="stat-label">赛段冠军 | 总冠军</div>
        </div>

        <div
          class="stat-card"
          :class="{ active: activeTab === 'teams' }"
          @click="setActiveTab('teams')"
          role="button"
          tabindex="0"
        >
          <div class="stat-icon">👥</div>
          <div class="stat-value">{{ riderDetail.stats.teams.length }}</div>
          <div class="stat-label">效力车队</div>
        </div>

        <div
          class="stat-card"
          :class="{ active: activeTab === 'ratings' }"
          @click="setActiveTab('ratings')"
          role="button"
          tabindex="0"
        >
          <div class="stat-icon">⭐</div>
          <div class="stat-value">
            {{ riderRatings?.stats?.average_score || '0.0' }}
          </div>
          <div class="stat-label">{{ riderRatings?.stats?.total_rating_count || 0 }} 人评价</div>
        </div>
      </div>

      <!-- 内容区域：根据 activeTab 显示不同内容 -->
      <div class="content-section">
        <!-- 评分与评价内容 -->
        <div v-if="activeTab === 'ratings'" class="tab-content">
          <div class="ratings-header">
            <h2 class="section-title">车手评价</h2>
            <button
              v-if="isLoggedIn"
              class="btn btn-primary action-button"
              @click="showRatingForm = !showRatingForm"
            >
              {{ riderRatings?.user_rating ? '修改评价' : '我要评价' }}
            </button>
            <div v-else class="login-tip">
              <router-link to="/login">登录</router-link> 后可参与评价
            </div>
          </div>

          <!-- 评分表单 -->
          <div v-if="showRatingForm" class="rating-form-card">
            <h3>{{ riderRatings?.user_rating ? '修改您的评价' : '发表新评价' }}</h3>
            <div class="form-group">
              <label>评分 (1-5星):</label>
              <div class="star-rating-input">
                <span
                  v-for="star in 5"
                  :key="star"
                  class="star-icon"
                  :class="{ active: star <= userScore }"
                  @click="userScore = star"
                >
                  ★
                </span>
                <span class="score-text">{{ userScore }} 分</span>
              </div>
            </div>
            <div class="form-group">
              <label>评价内容 (可选):</label>
              <textarea
                v-model="userComment"
                placeholder="说说您对这位车手的看法..."
                rows="3"
                maxlength="500"
              ></textarea>
            </div>
            <div class="form-actions">
              <button class="btn btn-secondary cancel-btn" @click="showRatingForm = false">
                取消
              </button>
              <button
                v-if="riderRatings?.user_rating"
                class="btn btn-danger delete-btn"
                @click="handleRatingDelete"
                :disabled="isSubmittingRating"
              >
                {{ isSubmittingRating ? '删除中...' : '删除评价' }}
              </button>
              <button
                class="btn btn-primary submit-btn"
                @click="handleRatingSubmit"
                :disabled="isSubmittingRating"
              >
                {{ isSubmittingRating ? '提交中...' : '提交评价' }}
              </button>
            </div>
          </div>

          <!-- 评价列表 -->
          <div v-if="isLoadingRatings" class="loading-state">加载评价中...</div>
          <div v-else-if="!ratingsList || ratingsList.data.length === 0" class="empty-state">
            暂无评价，快来抢沙发吧！
          </div>
          <div v-else class="ratings-list">
            <div v-for="rating in ratingsList.data" :key="rating.rating_id" class="rating-item">
              <div class="rating-header">
                <span class="user-name">{{ rating.user_nickname || '匿名用户' }}</span>
                <span class="rating-stars">
                  <span
                    v-for="n in 5"
                    :key="n"
                    class="star-small"
                    :class="{ filled: n <= rating.score }"
                    >★</span
                  >
                </span>
                <span class="rating-date">{{ formatDate(rating.created_at) }}</span>
              </div>
              <div class="rating-content">
                {{ rating.comment || '该用户没有填写文字评价。' }}
              </div>
            </div>

            <!-- 分页控件 -->
            <div v-if="ratingsList.pagination.total_pages > 1" class="pagination">
              <button
                :disabled="!ratingsList.pagination.has_prev"
                @click="loadRatingsList(ratingsList.pagination.page - 1)"
              >
                上一页
              </button>
              <span>
                第 {{ ratingsList.pagination.page }} / {{ ratingsList.pagination.total_pages }} 页
              </span>
              <button
                :disabled="!ratingsList.pagination.has_next"
                @click="loadRatingsList(ratingsList.pagination.page + 1)"
              >
                下一页
              </button>
            </div>
          </div>
        </div>

        <!-- GC 历史内容 -->
        <div v-if="activeTab === 'gc'" class="tab-content">
          <h2 class="section-title">总成绩排名历史</h2>
          <div v-if="isLoadingGCHistory" class="loading-state">加载中...</div>
          <div v-else-if="!riderGCHistory || riderGCHistory.data.length === 0" class="empty-state">
            暂无总成绩记录
          </div>
          <div v-else class="records-container">
            <div class="records-summary">
              共参加了 <strong>{{ riderGCHistory.pagination.total }}</strong> 届赛事的总成绩排名
            </div>
            <div class="records-table-wrap">
              <table class="records-table">
                <thead>
                  <tr>
                    <th>年份</th>
                    <th>赛事</th>
                    <th>排名</th>
                    <th>用时/差距</th>
                    <th>车队</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="record in riderGCHistory.data"
                    :key="record.gc_id"
                    :class="{ 'win-row': record.rank === 1 }"
                  >
                    <td class="year-cell">{{ record.year }}</td>
                    <td class="race-cell">{{ record.race_name }}</td>
                    <td class="rank-cell" :class="{ 'rank-first': record.rank === 1 }">
                      <span v-if="record.rank === 1" class="trophy">🏆</span>
                      {{ record.rank }}
                    </td>
                    <td class="time-cell">
                      {{
                        record.gap_in_seconds
                          ? `+ ${formatTime(record.gap_in_seconds)}`
                          : formatTime(record.time_in_seconds)
                      }}
                    </td>
                    <td class="team-cell">{{ record.team_name }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- 分页控件 -->
            <div v-if="riderGCHistory.pagination.total_pages > 1" class="pagination">
              <button
                class="pagination-btn"
                :disabled="!riderGCHistory.pagination.has_prev"
                @click="loadGCHistoryPage(gcHistoryCurrentPage - 1)"
              >
                上一页
              </button>
              <span class="pagination-info">
                第 {{ riderGCHistory.pagination.page }} /
                {{ riderGCHistory.pagination.total_pages }} 页
              </span>
              <button
                class="pagination-btn"
                :disabled="!riderGCHistory.pagination.has_next"
                @click="loadGCHistoryPage(gcHistoryCurrentPage + 1)"
              >
                下一页
              </button>
            </div>
          </div>
        </div>

        <!-- 参赛场次内容 -->
        <div v-if="activeTab === 'races'" class="tab-content">
          <h2 class="section-title">参赛场次详情</h2>
          <div v-if="isLoadingRaces" class="loading-state">加载中...</div>
          <div v-else-if="!riderRaces || riderRaces.data.length === 0" class="empty-state">
            暂无参赛记录
          </div>
          <div v-else class="records-container">
            <div class="records-summary">
              共参加了 <strong>{{ riderRaces.pagination.total }}</strong> 个赛段
            </div>
            <div class="records-table-wrap">
              <table class="records-table">
                <thead>
                  <tr>
                    <th>年份</th>
                    <th>赛事</th>
                    <th>赛段</th>
                    <th>路线</th>
                    <th>排名</th>
                    <th>用时</th>
                    <th>车队</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="record in riderRaces.data"
                    :key="record.result_id"
                    :class="{ 'win-row': record.rank === 1 }"
                  >
                    <td class="year-cell">{{ record.year }}</td>
                    <td class="race-cell">{{ record.race_name }}</td>
                    <td class="stage-cell">{{ formatStageName(record.stage_number) }}</td>
                    <td class="route-cell">{{ record.stage_route }}</td>
                    <td class="rank-cell" :class="{ 'rank-first': record.rank === 1 }">
                      <span v-if="record.rank === 1" class="trophy">🏆</span>
                      {{ record.rank }}
                    </td>
                    <td class="time-cell">{{ formatTime(record.time_in_seconds) }}</td>
                    <td class="team-cell">{{ record.team_name }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- 分页控件 -->
            <div v-if="riderRaces.pagination.total_pages > 1" class="pagination">
              <button
                class="pagination-btn"
                :disabled="!riderRaces.pagination.has_prev"
                @click="loadRacesPage(racesCurrentPage - 1)"
              >
                上一页
              </button>
              <span class="pagination-info">
                第 {{ riderRaces.pagination.page }} / {{ riderRaces.pagination.total_pages }} 页
              </span>
              <button
                class="pagination-btn"
                :disabled="!riderRaces.pagination.has_next"
                @click="loadRacesPage(racesCurrentPage + 1)"
              >
                下一页
              </button>
            </div>
          </div>
        </div>

        <!-- 赛段冠军内容 -->
        <div v-if="activeTab === 'wins'" class="tab-content">
          <h2 class="section-title">冠军记录</h2>
          <div v-if="isLoadingWins" class="loading-state">加载中...</div>
          <div
            v-else-if="
              !riderWins ||
              (riderWins.win_records.length === 0 &&
                (!riderWins.gc_win_records || riderWins.gc_win_records.length === 0))
            "
            class="empty-state"
          >
            该车手暂无冠军记录
          </div>
          <div v-else class="records-container">
            <!-- GC Wins -->
            <div
              v-if="riderWins.gc_win_records && riderWins.gc_win_records.length > 0"
              class="wins-section"
            >
              <h3 class="subsection-title">总成绩冠军 (GC)</h3>
              <div class="records-summary wins-summary">
                共获得
                <strong class="wins-count">{{ riderDetail.stats.gc_wins }}</strong> 个总成绩冠军
              </div>
              <div class="wins-grid">
                <div
                  v-for="win in riderWins.gc_win_records"
                  :key="win.gc_id"
                  class="win-card gc-win-card"
                >
                  <div class="win-header">
                    <span class="win-trophy">🏆</span>
                    <div class="win-title">
                      <div class="win-race">{{ win.race_name }} {{ win.year }}</div>
                      <div class="win-stage">General Classification</div>
                    </div>
                  </div>
                  <div class="win-footer">
                    <span class="win-time">⏱️ {{ formatTime(win.time_in_seconds) }}</span>
                    <span class="win-team">🚴 {{ win.team_name }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Stage Wins -->
            <div v-if="riderWins.win_records.length > 0" class="wins-section">
              <h3 class="subsection-title">赛段冠军</h3>
              <div class="records-summary wins-summary">
                共获得
                <strong class="wins-count">{{ riderDetail.stats.stage_wins }}</strong> 个赛段冠军
              </div>
              <div class="wins-grid">
                <div v-for="win in riderWins.win_records" :key="win.result_id" class="win-card">
                  <div class="win-header">
                    <span class="win-trophy">🏆</span>
                    <div class="win-title">
                      <div class="win-race">{{ win.race_name }} {{ win.year }}</div>
                      <div class="win-stage">{{ formatStageName(win.stage_number) }}</div>
                    </div>
                  </div>
                  <div class="win-route">{{ win.stage_route }}</div>
                  <div class="win-footer">
                    <span class="win-time">⏱️ {{ formatTime(win.time_in_seconds) }}</span>
                    <span class="win-team">🚴 {{ win.team_name }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 效力车队列表 -->
        <div v-if="activeTab === 'teams'" class="tab-content">
          <h2 class="section-title">效力车队历史</h2>
          <div v-if="riderDetail.stats.teams.length === 0" class="empty-state">
            该车手暂无车队记录
          </div>
          <div v-else class="teams-list">
            <div v-for="team in riderDetail.stats.teams" :key="team.team_id" class="team-item">
              <span class="team-badge">🚴</span>
              <span class="team-name">{{ team.team_name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ============ CSS 变量定义 ============ */
.detail-container {
  /* 色值变量 */
  --color-primary: #3b82f6;
  --color-primary-dark: #2563eb;
  --color-danger: #ef4444;
  --color-danger-dark: #dc2626;
  --color-warning: #fbbf24;
  --color-warning-dark: #f59e0b;
  --color-warning-light: #fcd34d;
  --color-white: white;
  --color-text-dark: #1e293b;
  --color-text-base: #475569;
  --color-text-light: #64748b;
  --color-text-lighter: #94a3b8;
  --color-bg-light: #f8fafc;
  --color-bg-lighter: #f1f5f9;
  --color-border: #e2e8f0;
  --color-border-light: #cbd5e1;

  /* 过渡与间距变量 */
  --transition: all 0.2s ease;
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
  --radius-2xl: 1.5rem;
  --radius-full: 9999px;

  /* 布局 */
  min-height: 100vh;
  background: linear-gradient(to bottom, #fffbf0, #fff9f0);
  padding: 2rem;
  font-family:
    'Inter',
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    Roboto,
    sans-serif;
}

.page-header {
  margin-bottom: 2rem;
}

.back-button {
  padding: 0.75rem 1.25rem;
  background: var(--color-white);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-base);
  cursor: pointer;
  transition: var(--transition);
}

.back-button:hover {
  background: var(--color-warning);
  color: #1e3a8a;
  border-color: var(--color-warning);
}

.status-message {
  max-width: 600px;
  margin: 2rem auto;
  padding: 1.5rem;
  border-radius: var(--radius-lg);
  text-align: center;
  font-weight: 500;
}

.error-message {
  background: #fef2f2;
  color: #b91c1c;
}

.loading-message {
  background: #eff6ff;
  color: #1d4ed8;
}

.rider-detail {
  max-width: 900px;
  margin: 0 auto;
}

.card {
  background: var(--color-white);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.info-card {
  background: var(--color-white);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  padding: 3rem 2rem;
  text-align: center;
  margin-bottom: 2rem;
}

.rider-avatar-large {
  width: 120px;
  height: 120px;
  margin: 0 auto 1.5rem;
  background: linear-gradient(135deg, var(--color-warning), var(--color-warning-dark));
  color: var(--color-white);
  font-size: 3rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  box-shadow: 0 8px 20px rgba(251, 191, 36, 0.4);
}

.rider-name-large {
  font-size: 2.5rem;
  font-weight: 800;
  color: #1e3a8a;
  margin-bottom: 0.75rem;
}

.rider-id-badge {
  display: inline-block;
  padding: 0.5rem 1rem;
  background: #fef3c7;
  color: #b45309;
  border-radius: var(--radius-full);
  font-size: 0.875rem;
  font-weight: 600;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: var(--color-white);
  border-radius: var(--radius-xl);
  padding: 2rem 1.5rem;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: var(--transition);
  cursor: pointer;
  border: 3px solid transparent;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.stat-card.active {
  border-color: var(--color-warning);
  box-shadow: 0 4px 16px rgba(251, 191, 36, 0.3);
  transform: translateY(-2px);
}

.highlight-card {
  background: linear-gradient(135deg, var(--color-warning-light), var(--color-warning));
  box-shadow: 0 4px 12px rgba(251, 191, 36, 0.4);
  border: 2px solid var(--color-warning-dark);
}

.stat-icon {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
}

.stat-value {
  font-size: 2.5rem;
  font-weight: 800;
  color: var(--color-text-dark);
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.875rem;
  color: var(--color-text-light);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.content-section {
  background: var(--color-white);
  border-radius: var(--radius-2xl);
  padding: 2rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  min-height: 300px;
}

.tab-content {
  animation: fadeIn 0.3s ease-in;
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

.info-message {
  text-align: center;
  padding: 3rem 2rem;
  color: var(--color-text-base);
}

.info-message p {
  font-size: 1.125rem;
  margin-bottom: 1rem;
  line-height: 1.6;
}

.info-message strong {
  color: #1e3a8a;
  font-weight: 700;
  font-size: 1.25rem;
}

.sub-text {
  color: var(--color-text-lighter);
  font-size: 0.875rem;
  font-style: italic;
}

.records-container {
  padding: 1rem 0;
}

.records-summary {
  text-align: center;
  padding: 1rem 2rem;
  margin-bottom: 1.5rem;
  background: var(--color-bg-light);
  border-radius: var(--radius-lg);
  font-size: 1.125rem;
  color: var(--color-text-base);
}

.records-summary strong {
  color: var(--color-text-dark);
  font-size: 1.5rem;
  font-weight: 800;
}

.wins-summary {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
}

.wins-count {
  color: #b45309 !important;
}

.records-table-wrap {
  overflow-x: auto;
  border-radius: var(--radius-md);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.records-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-white);
  font-size: 0.875rem;
}

.records-table thead {
  background: var(--color-bg-lighter);
  position: sticky;
  top: 0;
  z-index: 10;
}

.records-table th {
  padding: 0.75rem 0.5rem;
  text-align: left;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-text-light);
  border-bottom: 2px solid var(--color-border);
}

/* ============ 通用按钮样式 ============ */
.btn {
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-weight: 600;
  transition: var(--transition);
  border: none;
  font-family: inherit;
  font-size: 0.95rem;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-primary {
  background-color: var(--color-primary);
  color: var(--color-white);
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--color-primary-dark);
}

.btn-danger {
  background-color: var(--color-danger);
  color: var(--color-white);
}

.btn-danger:hover:not(:disabled) {
  background-color: var(--color-danger-dark);
}

.btn-secondary {
  background: transparent;
  border: 1px solid var(--color-border-light);
  color: var(--color-text-light);
}

.btn-secondary:hover:not(:disabled) {
  background-color: var(--color-bg-lighter);
  border-color: var(--color-text-lighter);
}

/* 按钮大小变体 */
.btn.submit-btn {
  padding: 0.5rem 1.5rem;
}

/* ============ 表单样式 ============ */
.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: var(--color-text-base);
}

textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  font-family: inherit;
  resize: vertical;
}

/* ============ 评分相关样式 ============ */
.ratings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.login-tip {
  color: var(--color-text-light);
  font-size: 0.875rem;
}

.login-tip a {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 600;
}

.rating-form-card {
  background: var(--color-bg-light);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.rating-form-card h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: var(--color-text-dark);
}

.star-rating-input {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.star-icon {
  font-size: 2rem;
  color: var(--color-border-light);
  cursor: pointer;
  transition: color 0.2s;
}

.star-icon.active {
  color: var(--color-warning);
}

.score-text {
  margin-left: 1rem;
  font-weight: 600;
  color: var(--color-text-light);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1rem;
}

/* ============ 卡片公共样式 ============ */
.card-base {
  border-radius: var(--radius-md);
  padding: 1rem;
  margin-bottom: 1rem;
  border: 1px solid var(--color-border);
  transition: var(--transition);
}

.rating-item {
  border-radius: var(--radius-md);
  padding: 1rem;
  margin-bottom: 1rem;
  border: 1px solid var(--color-border);
  transition: var(--transition);
  background: var(--color-white);
}

.rating-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.user-name {
  font-weight: 600;
  color: var(--color-text-dark);
}

.star-small {
  color: var(--color-border-light);
  font-size: 1rem;
}

.star-small.filled {
  color: var(--color-warning);
}

.rating-date {
  margin-left: auto;
  color: var(--color-text-lighter);
  font-size: 0.875rem;
}

.rating-content {
  color: var(--color-text-base);
  line-height: 1.5;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
}

.pagination button {
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-border);
  background: var(--color-white);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition);
}

.pagination button:hover:not(:disabled) {
  background: var(--color-bg-light);
  border-color: var(--color-text-light);
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.records-table td {
  padding: 0.75rem 0.5rem;
  border-bottom: 1px solid #f1f5f9;
}

.records-table tbody tr {
  transition: background-color 0.15s ease;
}

.records-table tbody tr:hover {
  background-color: var(--color-bg-light);
}

.records-table tbody tr.win-row {
  background-color: #fefce8;
}

.records-table tbody tr.win-row:hover {
  background-color: #fef9c3;
}

/* 表格单元格样式 */
.cell-primary {
  font-weight: 600;
  color: var(--color-text-dark);
}

.cell-secondary {
  color: var(--color-text-base);
  font-weight: 500;
}

.cell-tertiary {
  color: var(--color-text-light);
  font-size: 0.8rem;
}

.year-cell {
  font-weight: 600;
  color: var(--color-text-dark);
}

.race-cell {
  color: var(--color-text-base);
  font-weight: 500;
}

.stage-cell {
  color: var(--color-text-light);
  font-size: 0.8rem;
}

.route-cell {
  color: var(--color-text-light);
  font-size: 0.8rem;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank-cell {
  font-weight: 700;
  color: var(--color-text-dark);
  text-align: center;
}

.rank-first {
  color: #b45309;
  font-size: 1.1rem;
}

.trophy {
  margin-right: 0.25rem;
}

.time-cell {
  font-family: 'Courier New', monospace;
  color: var(--color-text-base);
  font-weight: 500;
}

.team-cell {
  color: var(--color-text-light);
  font-size: 0.8rem;
}

/* 冠军卡片网格 */
.wins-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.25rem;
  padding: 0.5rem 0;
}

.win-card {
  background: linear-gradient(135deg, #fffbeb, #fef3c7);
  border: 2px solid var(--color-warning);
  border-radius: var(--radius-xl);
  padding: 1.5rem;
  transition: var(--transition);
  box-shadow: 0 2px 8px rgba(251, 191, 36, 0.2);
}

.win-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 16px rgba(251, 191, 36, 0.3);
}

.win-header {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.win-trophy {
  font-size: 2rem;
  flex-shrink: 0;
}

.win-title {
  flex: 1;
}

.win-race {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text-dark);
  margin-bottom: 0.25rem;
}

.win-stage {
  font-size: 0.875rem;
  font-weight: 600;
  color: #b45309;
}

.win-route {
  font-size: 0.875rem;
  color: var(--color-text-light);
  margin-bottom: 1rem;
  line-height: 1.5;
}

.win-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(251, 191, 36, 0.3);
  font-size: 0.8rem;
  color: var(--color-text-light);
  font-weight: 500;
}

.win-time,
.win-team {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text-dark);
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid var(--color-border);
}

.teams-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}

.team-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  background: var(--color-bg-light);
  border-radius: var(--radius-lg);
  transition: var(--transition);
}

.team-item:hover {
  background: var(--color-bg-lighter);
  transform: translateX(4px);
}

.team-badge {
  font-size: 1.5rem;
}

.team-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #334155;
  flex: 1;
}

.subsection-title {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--color-text-dark);
  margin: 1.5rem 0 1rem;
  padding-left: 0.75rem;
  border-left: 4px solid var(--color-primary);
}

.wins-section + .wins-section {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px dashed var(--color-border);
}

@media (max-width: 768px) {
  .rider-name-large {
    font-size: 2rem;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .teams-list {
    grid-template-columns: 1fr;
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
