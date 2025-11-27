<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { ApiRiderDetail, ApiRiderRaces, ApiRiderWins } from '@/interfaces/types'
import { fetchRiderDetail, fetchRiderRaces, fetchRiderWins } from '@/services/ApiServices'

const router = useRouter()
const route = useRoute()

const riderDetail = ref<ApiRiderDetail | null>(null)
const riderRaces = ref<ApiRiderRaces | null>(null)
const riderWins = ref<ApiRiderWins | null>(null)

const isLoading = ref<boolean>(false)
const isLoadingRaces = ref<boolean>(false)
const isLoadingWins = ref<boolean>(false)
const error = ref<string | null>(null)

// 当前激活的标签页: 'races' | 'wins' | 'teams'
const activeTab = ref<'races' | 'wins' | 'teams'>('teams')

const loadRiderDetail = async () => {
  const riderId = Number(route.params.id)
  if (isNaN(riderId)) {
    error.value = '无效的车手 ID'
    return
  }

  isLoading.value = true
  error.value = null
  try {
    riderDetail.value = await fetchRiderDetail(riderId)
  } catch (err) {
    console.error(err)
    error.value = '无法加载车手详情，请检查后端服务'
  } finally {
    isLoading.value = false
  }
}

const goBack = () => {
  router.push('/riders')
}

const setActiveTab = async (tab: 'races' | 'wins' | 'teams') => {
  activeTab.value = tab

  const riderId = Number(route.params.id)

  // 根据选择的标签页加载对应数据（如果还没加载过）
  if (tab === 'races' && !riderRaces.value) {
    isLoadingRaces.value = true
    try {
      riderRaces.value = await fetchRiderRaces(riderId)
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

onMounted(() => {
  loadRiderDetail()
})
</script>

<template>
  <div class="detail-container">
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
          class="stat-card highlight-card"
          :class="{ active: activeTab === 'wins' }"
          @click="setActiveTab('wins')"
          role="button"
          tabindex="0"
        >
          <div class="stat-icon">🏆</div>
          <div class="stat-value">{{ riderDetail.stats.stage_wins }}</div>
          <div class="stat-label">赛段冠军</div>
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
      </div>

      <!-- 内容区域：根据 activeTab 显示不同内容 -->
      <div class="content-section">
        <!-- 参赛场次内容 -->
        <div v-if="activeTab === 'races'" class="tab-content">
          <h2 class="section-title">参赛场次详情</h2>
          <div v-if="isLoadingRaces" class="loading-state">加载中...</div>
          <div v-else-if="!riderRaces || riderRaces.race_records.length === 0" class="empty-state">
            暂无参赛记录
          </div>
          <div v-else class="records-container">
            <div class="records-summary">
              共参加了 <strong>{{ riderDetail.stats.total_races }}</strong> 个赛段
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
                    v-for="record in riderRaces.race_records"
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
          </div>
        </div>

        <!-- 赛段冠军内容 -->
        <div v-if="activeTab === 'wins'" class="tab-content">
          <h2 class="section-title">赛段冠军记录</h2>
          <div v-if="isLoadingWins" class="loading-state">加载中...</div>
          <div v-else-if="!riderWins || riderWins.win_records.length === 0" class="empty-state">
            该车手暂无赛段冠军记录
          </div>
          <div v-else class="records-container">
            <div class="records-summary wins-summary">
              共获得
              <strong class="wins-count">{{ riderDetail.stats.stage_wins }}</strong> 个赛段冠军 🏆
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
.detail-container {
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

.rider-detail {
  max-width: 900px;
  margin: 0 auto;
}

.info-card {
  background: white;
  border-radius: 1.5rem;
  padding: 3rem 2rem;
  text-align: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  margin-bottom: 2rem;
}

.rider-avatar-large {
  width: 120px;
  height: 120px;
  margin: 0 auto 1.5rem;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: white;
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
  border-radius: 9999px;
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
  background: white;
  border-radius: 1rem;
  padding: 2rem 1.5rem;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: all 0.2s ease;
  cursor: pointer;
  border: 3px solid transparent;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.stat-card.active {
  border-color: #fbbf24;
  box-shadow: 0 4px 16px rgba(251, 191, 36, 0.3);
  transform: translateY(-2px);
}

.highlight-card {
  background: linear-gradient(135deg, #fcd34d, #fbbf24);
  box-shadow: 0 4px 12px rgba(251, 191, 36, 0.4);
  border: 2px solid #f59e0b;
}

.stat-icon {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
}

.stat-value {
  font-size: 2.5rem;
  font-weight: 800;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.content-section {
  background: white;
  border-radius: 1.5rem;
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
  color: #475569;
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
  color: #94a3b8;
  font-size: 0.875rem;
  font-style: italic;
}

.loading-state {
  text-align: center;
  padding: 3rem;
  color: #64748b;
  font-size: 1.125rem;
}

.records-container {
  padding: 1rem 0;
}

.records-summary {
  text-align: center;
  padding: 1rem 2rem;
  margin-bottom: 1.5rem;
  background: #f8fafc;
  border-radius: 0.75rem;
  font-size: 1.125rem;
  color: #475569;
}

.records-summary strong {
  color: #1e3a8a;
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
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.records-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  font-size: 0.875rem;
}

.records-table thead {
  background: #f1f5f9;
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
  color: #64748b;
  border-bottom: 2px solid #e2e8f0;
}

.records-table td {
  padding: 0.75rem 0.5rem;
  border-bottom: 1px solid #f1f5f9;
}

.records-table tbody tr {
  transition: background-color 0.15s ease;
}

.records-table tbody tr:hover {
  background-color: #f8fafc;
}

.records-table tbody tr.win-row {
  background-color: #fefce8;
}

.records-table tbody tr.win-row:hover {
  background-color: #fef9c3;
}

.year-cell {
  font-weight: 600;
  color: #1e293b;
}

.race-cell {
  color: #475569;
  font-weight: 500;
}

.stage-cell {
  color: #64748b;
  font-size: 0.8rem;
}

.route-cell {
  color: #64748b;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank-cell {
  font-weight: 700;
  color: #1e293b;
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
  color: #475569;
  font-weight: 500;
}

.team-cell {
  color: #64748b;
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
  border: 2px solid #fbbf24;
  border-radius: 1rem;
  padding: 1.5rem;
  transition: all 0.2s ease;
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
  color: #1e293b;
  margin-bottom: 0.25rem;
}

.win-stage {
  font-size: 0.875rem;
  font-weight: 600;
  color: #b45309;
}

.win-route {
  font-size: 0.875rem;
  color: #64748b;
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
  color: #64748b;
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
  color: #1e293b;
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #e2e8f0;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #94a3b8;
  font-style: italic;
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
  background: #f8fafc;
  border-radius: 0.75rem;
  transition: all 0.2s ease;
}

.team-item:hover {
  background: #f1f5f9;
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
}
</style>
