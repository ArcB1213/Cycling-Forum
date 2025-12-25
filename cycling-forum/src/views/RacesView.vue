<script setup lang="ts">
// 1. 导入 Vue 核心和类型
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { Race, Edition, Stage, StageResult, PaginationMeta } from '@/interfaces/types'

// 2. 导入 API 服务
import {
  fetchRaces,
  fetchEditions,
  fetchStages,
  fetchResults,
  fetchEditionGCResults,
} from '@/services/ApiServices'

const router = useRouter()

const goBack = () => {
  router.push('/')
}

// 3. 类型安全的响应式状态
const races = ref<Race[]>([])
const editions = ref<Edition[]>([])
const stages = ref<Stage[]>([])
const results = ref<StageResult[]>([])
const gcResults = ref<any[]>([]) // Use any to avoid complex union types in template
const isGCSelected = ref(false)

const resultsPagination = ref<PaginationMeta | null>(null)
const currentResultsPage = ref<number>(1)
const resultsPageInputValue = ref<string>('')

const selectedRace = ref<Race | null>(null)
const selectedEdition = ref<Edition | null>(null)
const selectedStage = ref<Stage | null>(null)

// v-model friendly ids for <select>
const selectedRaceId = ref<number | null>(null)
const selectedEditionId = ref<number | null>(null)
const selectedStageId = ref<number | null>(null)

const isLoadingRaces = ref<boolean>(false)
const isLoadingEditions = ref<boolean>(false)
const isLoadingStages = ref<boolean>(false)
const isLoadingResults = ref<boolean>(false)

const error = ref<string | null>(null)

// 4. API 调用逻辑
onMounted(async () => {
  isLoadingRaces.value = true
  error.value = null
  try {
    races.value = await fetchRaces()
  } catch (err) {
    console.error(err)
    error.value = '无法连接到服务器。请确保后端正在运行。'
  } finally {
    isLoadingRaces.value = false
  }
})

const handleRaceSelect = async (race: Race) => {
  selectedRace.value = race
  selectedEdition.value = null // 重置
  selectedStage.value = null
  stages.value = []
  results.value = []

  isLoadingEditions.value = true
  try {
    const data = await fetchEditions(race.race_id)
    editions.value = data.editions
  } catch (err) {
    console.error(err)
    error.value = '加载届数失败'
  } finally {
    isLoadingEditions.value = false
  }
}

// wrappers for select change (use id -> find object -> call existing handlers)
const onRaceChange = async () => {
  if (selectedRaceId.value == null) {
    selectedRace.value = null
    editions.value = []
    stages.value = []
    results.value = []
    selectedEditionId.value = null
    selectedStageId.value = null
    return
  }
  const race = races.value.find((r) => r.race_id === selectedRaceId.value)
  if (race) await handleRaceSelect(race)
}

const onEditionChange = async () => {
  if (selectedEditionId.value == null || !selectedRace.value) {
    selectedEdition.value = null
    stages.value = []
    results.value = []
    gcResults.value = []
    selectedStageId.value = null
    isGCSelected.value = false
    return
  }

  // 记住之前选择的状态，以便切换届数后自动恢复
  const wasGCSelected = isGCSelected.value
  const previousStageNumber = selectedStage.value?.stage_number

  const edition = editions.value.find((e) => e.edition_id === selectedEditionId.value)
  if (edition) {
    await handleEditionSelect(edition)

    // 自动恢复之前的选择状态
    if (wasGCSelected) {
      // 之前选的是总成绩，自动加载新届的总成绩
      selectedStageId.value = -1
      isGCSelected.value = true
      await handleGCSelect()
    } else if (previousStageNumber !== undefined) {
      // 之前选的是某个赛段，尝试找到新届中对应的赛段
      const matchingStage = stages.value.find((s) => s.stage_number === previousStageNumber)
      if (matchingStage) {
        selectedStageId.value = matchingStage.stage_id
        await handleStageSelect(matchingStage)
      }
    }
  }
}

const onStageChange = async () => {
  if (selectedStageId.value === -1) {
    isGCSelected.value = true
    selectedStage.value = null
    results.value = []
    await handleGCSelect()
    return
  }
  isGCSelected.value = false

  if (selectedStageId.value == null) {
    selectedStage.value = null
    results.value = []
    return
  }
  const stage = stages.value.find((s) => s.stage_id === selectedStageId.value)
  if (stage) await handleStageSelect(stage)
}

const handleGCSelect = async (page: number = 1) => {
  if (!selectedEdition.value) return
  isLoadingResults.value = true
  currentResultsPage.value = page
  try {
    const data = await fetchEditionGCResults(selectedEdition.value.edition_id, page, 20)
    gcResults.value = data.data
    resultsPagination.value = data.pagination
  } catch (err) {
    console.error(err)
    error.value = '加载总成绩失败'
  } finally {
    isLoadingResults.value = false
  }
}

// keep watchers to keep select values in sync when selection happens via functions
watch(selectedRace, (val) => {
  selectedRaceId.value = val ? val.race_id : null
})
watch(selectedEdition, (val) => {
  selectedEditionId.value = val ? val.edition_id : null
})
watch(selectedStage, (val) => {
  selectedStageId.value = val ? val.stage_id : null
})

const handleEditionSelect = async (edition: Edition) => {
  selectedEdition.value = edition
  selectedStage.value = null
  results.value = []

  isLoadingStages.value = true
  try {
    const data = await fetchStages(edition.edition_id)
    stages.value = data.stages
  } catch (err) {
    console.error(err)
    error.value = '加载赛段失败'
  } finally {
    isLoadingStages.value = false
  }
}

const handleStageSelect = async (stage: Stage, page: number = 1) => {
  selectedStage.value = stage
  currentResultsPage.value = page
  isLoadingResults.value = true
  try {
    const data = await fetchResults(stage.stage_id, page, 20)
    results.value = data.data
    resultsPagination.value = data.pagination
  } catch (err) {
    console.error(err)
    error.value = '加载成绩失败'
  } finally {
    isLoadingResults.value = false
  }
}

// 分页控制函数
const goToResultsPage = (page: number) => {
  if (isGCSelected.value) {
    handleGCSelect(page)
  } else if (
    selectedStage.value &&
    page >= 1 &&
    page <= (resultsPagination.value?.total_pages || 1)
  ) {
    handleStageSelect(selectedStage.value, page)
  }
}

const nextResultsPage = () => {
  if (resultsPagination.value?.has_next) {
    goToResultsPage(currentResultsPage.value + 1)
  }
}

const prevResultsPage = () => {
  if (resultsPagination.value?.has_prev) {
    goToResultsPage(currentResultsPage.value - 1)
  }
}

const getResultsPageNumbers = () => {
  if (!resultsPagination.value) return []

  const current = currentResultsPage.value
  const total = resultsPagination.value.total_pages
  const pages = []

  const start = Math.max(1, current - 2)
  const end = Math.min(total, current + 2)

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  return pages
}

// 赛段成绩页码输入框跳转
const handleResultsPageInputKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter') {
    const page = parseInt(resultsPageInputValue.value, 10)
    if (page < 1) {
      goToResultsPage(1)
    } else if (page > (resultsPagination.value?.total_pages || 1)) {
      goToResultsPage(resultsPagination.value?.total_pages || 1)
    } else if (!isNaN(page)) {
      goToResultsPage(page)
    }

    resultsPageInputValue.value = ''
  }
}

const handleResultsPageInputBlur = () => {
  const page = parseInt(resultsPageInputValue.value, 10)
  if (!isNaN(page) && page >= 1 && page <= (resultsPagination.value?.total_pages || 1)) {
    goToResultsPage(page)
  }
  resultsPageInputValue.value = ''
}

// 5. 辅助函数 (Computed 和 Methods)
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

const selectedStageName = computed(() => {
  if (isGCSelected.value) return '总成绩排名 (GC)'
  return selectedStage.value
    ? `${formatStageName(selectedStage.value.stage_number)} 成绩`
    : '赛段成绩'
})
</script>

<template>
  <main class="container">
    <!-- 顶部导航栏 -->
    <header class="page-header">
      <button class="back-button" @click="goBack">← 返回主页</button>
      <h1 class="page-title">赛事数据浏览</h1>
    </header>

    <!-- 加载与错误状态 -->
    <div v-if="error" class="status-box error-box"><strong>加载出错:</strong> {{ error }}</div>
    <div v-if="isLoadingRaces" class="status-box info-box">正在加载赛事数据...</div>

    <!-- 顶部选择控件：赛事 / 届数 / 赛段 -->
    <div class="controls" role="region" aria-label="选择赛事和赛段">
      <div class="control">
        <label for="race-select">赛事</label>
        <select id="race-select" v-model="selectedRaceId" @change="onRaceChange">
          <option :value="null">选择赛事</option>
          <option v-for="race in races" :key="race.race_id" :value="race.race_id">
            {{ race.race_name }}
          </option>
        </select>
      </div>

      <div class="control">
        <label for="edition-select">届数</label>
        <select id="edition-select" v-model="selectedEditionId" @change="onEditionChange">
          <option :value="null">选择届数</option>
          <option v-for="edition in editions" :key="edition.edition_id" :value="edition.edition_id">
            {{ edition.year }}
          </option>
        </select>
      </div>

      <div class="control">
        <label for="stage-select">赛段</label>
        <select id="stage-select" v-model="selectedStageId" @change="onStageChange">
          <option :value="null">选择赛段</option>
          <option :value="-1" v-if="selectedEditionId">总成绩排名 (GC)</option>
          <option v-for="stage in stages" :key="stage.stage_id" :value="stage.stage_id">
            {{ formatStageName(stage.stage_number) }} - {{ stage.stage_route }}
          </option>
        </select>
      </div>
    </div>

    <!-- 成绩显示区（下方主体） -->
    <section class="results-section">
      <h2 class="card-header">
        {{ selectedStageName }}
        <span v-if="resultsPagination" class="results-count">
          （共 {{ resultsPagination.total }} 条成绩）
        </span>
      </h2>
      <div class="results-wrap">
        <div v-if="!selectedStage && !isGCSelected" class="placeholder">
          请先选择一个赛段或总成绩
        </div>
        <div v-else-if="isLoadingResults" class="placeholder">加载成绩中...</div>
        <div v-else>
          <table class="results-table">
            <thead class="sticky-header">
              <tr>
                <th>排名</th>
                <th>车手</th>
                <th>{{ isGCSelected ? '时间/差距' : '时间' }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="result in isGCSelected ? gcResults : results"
                :key="isGCSelected ? result.gc_id : result.result_id"
              >
                <td class="rank">{{ result.rank }}</td>
                <td class="rider">
                  <div class="rider-name">{{ result.rider_name }}</div>
                  <div class="team-name">{{ result.team_name }}</div>
                </td>
                <td class="time">
                  {{
                    isGCSelected && result.gap_in_seconds
                      ? `+ ${formatTime(result.gap_in_seconds)}`
                      : formatTime(result.time_in_seconds)
                  }}
                </td>
              </tr>
            </tbody>
          </table>

          <!-- 分页控件 -->
          <div v-if="resultsPagination && resultsPagination.total_pages > 1" class="pagination">
            <button
              class="pagination-button"
              :disabled="!resultsPagination.has_prev"
              @click="prevResultsPage"
            >
              ← 上一页
            </button>

            <div class="pagination-info">
              <span class="page-info-text">
                第 {{ resultsPagination.page }} / {{ resultsPagination.total_pages }} 页
              </span>
              <span class="page-numbers">
                <button
                  v-for="page in getResultsPageNumbers()"
                  :key="page"
                  :class="['page-number', { active: page === currentResultsPage }]"
                  @click="goToResultsPage(page)"
                >
                  {{ page }}
                </button>
              </span>

              <div class="page-input-wrapper">
                <span class="page-input-label">跳转到：</span>
                <input
                  v-model="resultsPageInputValue"
                  type="number"
                  min="1"
                  :max="resultsPagination.total_pages"
                  placeholder="页码"
                  class="page-input"
                  @keydown="handleResultsPageInputKeydown"
                  @blur="handleResultsPageInputBlur"
                />
                <span class="page-input-unit">页</span>
              </div>
            </div>

            <button
              class="pagination-button"
              :disabled="!resultsPagination.has_next"
              @click="nextResultsPage"
            >
              下一页 →
            </button>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
/* * 我们在这里使用 <style scoped> 替代 Tailwind，
 * 因为在多文件项目中设置 Tailwind 涉及额外的配置 (postcss.config.js, tailwind.config.js)。
 * 这里的样式模拟了 Tailwind 的外观。
 */

.container {
  min-height: 100vh;
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem;
  font-family:
    Inter,
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    Roboto,
    sans-serif;
  color: #1e293b; /* slate-800 */
  background-color: #fffbf0; /* cream background */
}

/* 顶部导航栏 */
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
  color: #1e293b;
  border-color: #fbbf24;
}

.page-title {
  font-size: 2rem;
  font-weight: 800;
  color: #1e3a8a;
}

/* 状态框 */
.status-box {
  margin-bottom: 1rem;
  padding: 1rem;
  border-radius: 0.5rem;
}
.error-box {
  background-color: #fef2f2; /* red-50 */
  color: #b91c1c; /* red-700 */
}
.info-box {
  background-color: #eff6ff; /* blue-50 */
  color: #1d4ed8; /* blue-700 */
}

/* 顶部选择控件 */
.controls {
  display: flex;
  gap: 1rem;
  align-items: end;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}
.control {
  display: flex;
  flex-direction: column;
  min-width: 220px;
}
.controls label {
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: #1e3a8a;
  font-size: 0.95rem;
}
.controls select {
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #e2e8f0;
  background: white;
  font-weight: 600;
  color: #0f172a;
}

/* 成绩区域为页面主体 */
.results-section {
  background-color: white;
  border-radius: 0.5rem;
  padding: 1rem;
  box-shadow:
    0 6px 18px rgba(2, 6, 23, 0.08),
    0 2px 6px rgba(2, 6, 23, 0.04);
}
.results-wrap {
  max-height: 75vh;
  overflow: auto;
  padding-bottom: 0.5rem;
}

@media (max-width: 767px) {
  .controls {
    flex-direction: column;
    align-items: stretch;
  }
  .control {
    min-width: 100%;
  }
  .controls select {
    width: 100%;
  }
}

/* 卡片样式 */
.data-card {
  display: flex;
  flex-direction: column;
  background-color: white;
  border-radius: 0.5rem;
  box-shadow:
    0 4px 6px -1px rgb(0 0 0 / 0.1),
    0 2px 4px -2px rgb(0 0 0 / 0.1);
}

.card-header {
  border-bottom: 3px solid #fbbf24; /* yellow border */
  padding: 1rem;
  margin-bottom: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e3a8a; /* dark blue text */
}

/* 可滚动的数据列 */
.data-column {
  flex-grow: 1;
  overflow-y: auto;
  padding: 0.5rem;
  max-height: 60vh;
}

.placeholder {
  padding: 0.75rem;
  text-align: center;
  color: #94a3b8; /* slate-400 */
}

/* 列表项 */
.list-item {
  display: block;
  cursor: pointer;
  border-radius: 0.375rem;
  padding: 0.75rem 0.5rem;
  font-size: 0.9rem;
  font-weight: 500;
  color: #334155; /* slate-700 */
  transition: background-color 0.15s ease;
}

.list-item:hover {
  background-color: #f1f5f9; /* slate-100 */
}

.list-item.selected {
  background-color: #fbbf24; /* yellow */
  color: #1e3a8a; /* dark blue text */
}
.list-item.selected strong {
  color: #1e3a8a;
}
.list-item strong {
  color: #0f172a; /* slate-900 */
}

/* 成绩表格 */
.results-table {
  width: 100%;
  border-collapse: collapse;
}
.results-table th,
.results-table td {
  padding: 0.75rem 0.5rem;
  text-align: left;
  white-space: nowrap;
  font-size: 0.875rem;
}
.results-table th {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: #64748b; /* slate-500 */
  border-bottom: 1px solid #e2e8f0; /* slate-200 */
}
.results-table .sticky-header th {
  position: sticky;
  top: 0;
  background-color: #f8fafc; /* slate-50 */
}

.results-table tbody tr:not(:last-child) {
  border-bottom: 1px solid #f1f5f9; /* slate-100 */
}

.results-table .rank {
  font-weight: 600;
  color: #0f172a; /* slate-900 */
}
.results-table .rider-name {
  font-weight: 500;
}
.results-table .team-name {
  font-size: 0.75rem;
  color: #64748b; /* slate-500 */
}
.results-table .time {
  font-family: monospace;
  color: #475569; /* slate-600 */
}

/* 分页控件样式 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
  padding: 1rem 0;
  border-top: 1px solid #e2e8f0;
}

.pagination-button {
  padding: 0.6rem 1.2rem;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 0.5rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pagination-button:hover:not(:disabled) {
  background: #fbbf24;
  color: #1e3a8a;
  border-color: #fbbf24;
  transform: translateY(-1px);
}

.pagination-button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.pagination-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.page-info-text {
  font-size: 0.9rem;
  color: #64748b;
  font-weight: 500;
}

.page-numbers {
  display: flex;
  gap: 0.5rem;
}

.page-number {
  min-width: 36px;
  height: 36px;
  padding: 0.4rem;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 0.4rem;
  font-size: 0.85rem;
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

.results-count {
  font-size: 0.9rem;
  color: #64748b;
  font-weight: 500;
  margin-left: 0.5rem;
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
  .pagination {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .pagination-info {
    flex-direction: column;
    gap: 0.5rem;
    width: 100%;
  }

  .page-info-text {
    text-align: center;
    width: 100%;
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
    padding: 0.5rem 1rem;
    font-size: 0.85rem;
  }
}
</style>
