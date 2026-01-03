<script setup lang="ts">
import '@/assets/common-styles.css'
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { Rider, PaginationMeta } from '@/interfaces/types'
import { fetchRiders } from '@/services/ApiServices'

const router = useRouter()

const riders = ref<Rider[]>([])
const searchQuery = ref<string>('')
const isLoading = ref<boolean>(false)
const error = ref<string | null>(null)

// 分页相关状态
const currentPage = ref<number>(1)
const pageSize = ref<number>(18)
const pagination = ref<PaginationMeta | null>(null)
const pageInputValue = ref<string>('')

// 排序相关状态
const sortBy = ref<string>('name')
const sortOptions = [
  { value: 'name', label: '按姓名排序' },
  { value: 'stage_wins', label: '按赛段冠军数' },
  { value: 'gc_wins', label: '按总成绩冠军数' },
  { value: 'rating_score', label: '按平均评分' },
]

// 搜索相关状态
const isSearchMode = ref<boolean>(false)
let searchDebounceTimer: number | null = null

// 加载车手数据
const loadRiders = async (page: number = 1, search?: string) => {
  isLoading.value = true
  error.value = null
  try {
    const response = await fetchRiders(page, pageSize.value, search, sortBy.value)
    riders.value = response.data
    pagination.value = response.pagination
    currentPage.value = page
    isSearchMode.value = !!search
  } catch (err) {
    console.error(err)
    error.value = '无法加载车手数据，请检查后端服务'
  } finally {
    isLoading.value = false
  }
}

// 排序变化处理
const onSortChange = () => {
  const search = searchQuery.value.trim() || undefined
  loadRiders(1, search) // 切换排序时回到第一页
}

// 搜索时直接显示后端返回的结果
const filteredRiders = computed(() => riders.value)

// 分页导航
const goToPage = (page: number) => {
  if (page >= 1 && page <= (pagination.value?.total_pages || 1)) {
    const search = searchQuery.value.trim() || undefined
    loadRiders(page, search)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

const nextPage = () => {
  if (pagination.value?.has_next) {
    goToPage(currentPage.value + 1)
  }
}

const prevPage = () => {
  if (pagination.value?.has_prev) {
    goToPage(currentPage.value - 1)
  }
}

// 导航到车手详情
const goToRiderDetail = (riderId: number) => {
  router.push(`/riders/${riderId}`)
}

// 返回主页
const goBack = () => {
  router.push('/')
}

// 辅助函数：生成页码数组
const getPageNumbers = () => {
  if (!pagination.value) return []

  const current = currentPage.value
  const total = pagination.value.total_pages
  const pages = []

  // 显示策略：当前页前后各2页
  const start = Math.max(1, current - 2)
  const end = Math.min(total, current + 2)

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  return pages
}

// 页码输入框跳转
const handlePageInputKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter') {
    const page = parseInt(pageInputValue.value, 10)
    if (!isNaN(page) && page >= 1 && page <= (pagination.value?.total_pages || 1)) {
      goToPage(page)
      pageInputValue.value = ''
    } else {
      pageInputValue.value = ''
    }

    if (page < 1) {
      goToPage(1)
    } else if (page > (pagination.value?.total_pages || 1)) {
      goToPage(pagination.value?.total_pages || 1)
    } else if (!isNaN(page)) {
      goToPage(page)
    }
    pageInputValue.value = ''
  }
}

const handlePageInputBlur = () => {
  const page = parseInt(pageInputValue.value, 10)
  if (!isNaN(page) && page >= 1 && page <= (pagination.value?.total_pages || 1)) {
    goToPage(page)
  }
  pageInputValue.value = ''
}

// 清除搜索
const clearSearch = () => {
  searchQuery.value = ''
  isSearchMode.value = false
  loadRiders(1) // 返回第一页
}

// 监听搜索框变化，使用防抖
watch(searchQuery, (newVal) => {
  // 清除之前的定时器
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }

  const query = newVal.trim()

  // 如果搜索框为空，返回正常分页模式
  if (!query) {
    clearSearch()
    return
  }

  // 防抖：400ms 后执行搜索
  searchDebounceTimer = setTimeout(() => {
    loadRiders(1, query)
  }, 400) as unknown as number
})

// 初始化
loadRiders()
</script>

<template>
  <div class="page-container">
    <!-- 顶部导航栏 -->
    <header class="page-header">
      <button class="back-button" @click="goBack">← 返回主页</button>
      <h1 class="page-title">车手信息</h1>
    </header>

    <!-- 搜索框和排序 -->
    <div class="search-section">
      <div class="search-and-sort">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索车手姓名..."
            class="search-input"
          />
          <span v-if="searchQuery" class="clear-button" @click="searchQuery = ''">✕</span>
        </div>
        <div class="sort-box">
          <label for="sort-select" class="sort-label">排序：</label>
          <select id="sort-select" v-model="sortBy" @change="onSortChange" class="sort-select">
            <option v-for="opt in sortOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>
      </div>
      <p class="search-hint">
        <span v-if="isSearchMode">
          搜索 "{{ searchQuery }}" 找到 {{ pagination?.total || 0 }} 位车手
          <span v-if="pagination && pagination.total_pages > 1">
            ，第 {{ pagination.page }} / {{ pagination.total_pages }} 页
          </span>
        </span>
        <span v-else>
          当前页显示 {{ filteredRiders.length }} 位车手
          <span v-if="pagination">
            | 共 {{ pagination.total }} 位车手，第 {{ pagination.page }} /
            {{ pagination.total_pages }} 页
          </span>
        </span>
      </p>
    </div>

    <!-- 加载与错误状态 -->
    <div v-if="error" class="status-message error-message">{{ error }}</div>
    <div v-if="isLoading" class="status-message loading-message">加载车手数据中...</div>

    <!-- 车手列表 -->
    <div v-else class="riders-grid">
      <div
        v-for="rider in filteredRiders"
        :key="rider.rider_id"
        class="rider-card"
        @click="goToRiderDetail(rider.rider_id)"
      >
        <div class="rider-avatar">{{ rider.rider_name.charAt(0) }}</div>
        <h3 class="rider-name">{{ rider.rider_name }}</h3>
        <p v-if="sortBy === 'stage_wins'" class="rider-wins">🏆 {{ rider.wins || 0 }} 赛段冠军</p>
        <p v-else-if="sortBy === 'gc_wins'" class="rider-wins">
          🥇 {{ rider.wins || 0 }} 总成绩冠军
        </p>
        <p v-else-if="sortBy === 'rating_score'" class="rider-rating">
          ⭐ {{ rider.avg_rating?.toFixed(1) || '0.0' }} 分
          <span class="rating-count">({{ rider.rating_count || 0 }} 人评价)</span>
        </p>
        <p v-else class="rider-id">ID: {{ rider.rider_id }}</p>
      </div>

      <!-- 无搜索结果 -->
      <div v-if="filteredRiders.length === 0 && !isLoading" class="no-results">
        <p v-if="isSearchMode">未找到匹配 "{{ searchQuery }}" 的车手</p>
        <p v-else>暂无车手数据</p>
        <button v-if="isSearchMode" @click="clearSearch" class="reset-button">清空搜索</button>
      </div>
    </div>

    <!-- 分页控件 -->
    <div v-if="pagination && filteredRiders.length > 0" class="pagination">
      <button class="pagination-button" :disabled="!pagination.has_prev" @click="prevPage">
        ← 上一页
      </button>

      <div class="pagination-info">
        <span class="page-numbers">
          <button
            v-for="page in getPageNumbers()"
            :key="page"
            :class="['page-number', { active: page === currentPage }]"
            @click="goToPage(page)"
          >
            {{ page }}
          </button>
        </span>

        <div class="page-input-wrapper">
          <span class="page-input-label">跳转到：</span>
          <input
            v-model="pageInputValue"
            type="number"
            min="1"
            :max="pagination.total_pages"
            placeholder="页码"
            class="page-input"
            @keydown="handlePageInputKeydown"
            @blur="handlePageInputBlur"
          />
          <span class="page-input-unit">页</span>
        </div>
      </div>

      <button class="pagination-button" :disabled="!pagination.has_next" @click="nextPage">
        下一页 →
      </button>
    </div>
  </div>
</template>

<style scoped>
/* 车手页面特定样式 */

.riders-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.rider-card {
  background: white;
  padding: 2rem 1.5rem;
  border-radius: 1rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.rider-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
}

.rider-avatar {
  width: 80px;
  height: 80px;
  margin: 0 auto 1rem;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: white;
  font-size: 2rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

.rider-name {
  font-size: 1.125rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.rider-id {
  font-size: 0.875rem;
  color: #94a3b8;
}

.rider-wins {
  font-size: 0.9rem;
  font-weight: 600;
  color: #f59e0b;
  margin-top: 0.25rem;
}

.rider-rating {
  font-size: 0.9rem;
  font-weight: 600;
  color: #f59e0b;
  margin-top: 0.25rem;
}

.rating-count {
  font-size: 0.75rem;
  color: #94a3b8;
  font-weight: 400;
}

.no-results p {
  font-size: 1.125rem;
  margin-bottom: 1.5rem;
}

@media (max-width: 768px) {
  .riders-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }
}
</style>
