<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import type { Rider } from '@/interfaces/types'
import { fetchRiders } from '@/services/ApiServices'

const router = useRouter()

const riders = ref<Rider[]>([])
const searchQuery = ref<string>('')
const isLoading = ref<boolean>(false)
const error = ref<string | null>(null)

// 加载所有车手
const loadRiders = async () => {
  isLoading.value = true
  error.value = null
  try {
    riders.value = await fetchRiders()
  } catch (err) {
    console.error(err)
    error.value = '无法加载车手数据，请检查后端服务'
  } finally {
    isLoading.value = false
  }
}

// 搜索过滤
const filteredRiders = computed(() => {
  if (!searchQuery.value.trim()) {
    return riders.value
  }
  const query = searchQuery.value.toLowerCase().trim()
  return riders.value.filter((rider) => rider.rider_name.toLowerCase().includes(query))
})

// 导航到车手详情
const goToRiderDetail = (riderId: number) => {
  router.push(`/riders/${riderId}`)
}

// 返回主页
const goBack = () => {
  router.push('/')
}

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
      <p class="search-hint">共找到 {{ filteredRiders.length }} 位车手</p>
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
        <p>未找到匹配的车手</p>
        <button @click="searchQuery = ''" class="reset-button">清空搜索</button>
      </div>
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

@media (max-width: 768px) {
  .riders-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }

  .page-title {
    font-size: 2rem;
  }
}
</style>
