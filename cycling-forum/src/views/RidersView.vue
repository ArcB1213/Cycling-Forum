<script setup lang="ts">
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

// 搜索相关状态
const isSearchMode = ref<boolean>(false)
let searchDebounceTimer: number | null = null

// 加载车手数据
const loadRiders = async (page: number = 1, search?: string) => {
  isLoading.value = true
  error.value = null
  try {
    const response = await fetchRiders(page, pageSize.value, search)
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
  <div class="riders-container">
    <!-- 顶部导航栏 -->
    <header class="page-header">
      <button class="back-button" @click="goBack">← 返回主页</button>
      <h1 class="page-title">车手信息</h1>
    </header>

    <!-- 搜索框 -->
    <div class="search-section">
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
        <p class="rider-id">ID: {{ rider.rider_id }}</p>
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
.riders-container {
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
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.back-button {
  padding: 0.75rem 1.25rem;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-button:hover {
  background: #fbbf24;
  color: #1e3a8a;
  border-color: #fbbf24;
}

.page-title {
  font-size: 2.5rem;
  font-weight: 800;
  color: #1e3a8a;
}

.search-section {
  max-width: 600px;
  margin: 0 auto 3rem;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: white;
  padding: 1rem 1.5rem;
  border-radius: 9999px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
  transition: box-shadow 0.2s ease;
}

.search-box:focus-within {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
}

.search-icon {
  font-size: 1.25rem;
  color: #94a3b8;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 1rem;
  color: #1e293b;
}

.search-input::placeholder {
  color: #cbd5e1;
}

.clear-button {
  font-size: 1.25rem;
  color: #94a3b8;
  cursor: pointer;
  transition: color 0.2s ease;
}

.clear-button:hover {
  color: #475569;
}

.search-hint {
  margin-top: 0.75rem;
  text-align: center;
  color: #64748b;
  font-size: 0.875rem;
}

.status-message {
  max-width: 600px;
  margin: 2rem auto;
  padding: 1.5rem;
  border-radius: 0.75rem;
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

.no-results {
  grid-column: 1 / -1;
  text-align: center;
  padding: 3rem 1rem;
  color: #64748b;
}

.no-results p {
  font-size: 1.125rem;
  margin-bottom: 1.5rem;
}

.reset-button {
  padding: 0.75rem 1.5rem;
  background: #fbbf24;
  color: #1e3a8a;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.reset-button:hover {
  background: #f59e0b;
}

/* 分页控件样式 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 3rem;
  padding: 2rem 0;
}

.pagination-button {
  padding: 0.75rem 1.5rem;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pagination-button:hover:not(:disabled) {
  background: #fbbf24;
  color: #1e3a8a;
  border-color: #fbbf24;
}

.pagination-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.page-numbers {
  display: flex;
  gap: 0.5rem;
}

.page-number {
  min-width: 40px;
  height: 40px;
  padding: 0.5rem;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
}

.page-number:hover {
  background: #fef3c7;
  border-color: #fbbf24;
}

.page-number.active {
  background: #fbbf24;
  color: #1e3a8a;
  border-color: #fbbf24;
}

/* 页码输入框样式 */
.page-input-wrapper {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #f8fafc;
  border-radius: 0.375rem;
  border: 1px solid #e2e8f0;
}

.page-input-label {
  font-size: 0.875rem;
  color: #64748b;
  white-space: nowrap;
}

.page-input {
  width: 60px;
  padding: 0.375rem 0.5rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  text-align: center;
  color: #1e293b;
  transition: all 0.2s ease;
}

.page-input:focus {
  outline: none;
  border-color: #fbbf24;
  box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.1);
}

.page-input::placeholder {
  color: #cbd5e1;
}

.page-input-unit {
  font-size: 0.875rem;
  color: #64748b;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .riders-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }

  .page-title {
    font-size: 2rem;
  }

  .pagination {
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .pagination-info {
    flex-direction: column;
    width: 100%;
    gap: 0.5rem;
  }

  .page-numbers {
    flex-wrap: wrap;
    justify-content: center;
  }

  .page-input-wrapper {
    justify-content: center;
    width: 100%;
  }

  .page-input {
    width: 50px;
    font-size: 0.8rem;
    padding: 0.3rem 0.4rem;
  }

  .pagination-button {
    padding: 0.6rem 1rem;
    font-size: 0.85rem;
  }
}
</style>
