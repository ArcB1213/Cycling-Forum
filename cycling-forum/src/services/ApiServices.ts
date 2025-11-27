import axios from 'axios'
import type {
  Race,
  ApiRaceEditions,
  ApiEditionStages,
  ApiStageResults,
  Rider,
  ApiRiderDetail,
  ApiRiderRaces,
  ApiRiderWins,
} from '@/interfaces/types' // 导入类型

// 你的 Flask 后端地址
const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:5000/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * 获取所有赛事
 */
export const fetchRaces = async (): Promise<Race[]> => {
  const response = await apiClient.get<Race[]>('/races')
  return response.data
}

/**
 * 获取某一赛事的所有届数 (年份)
 * @param raceId - 赛事的 ID
 */
export const fetchEditions = async (raceId: number): Promise<ApiRaceEditions> => {
  const response = await apiClient.get<ApiRaceEditions>(`/races/${raceId}/editions`)
  return response.data
}

/**
 * 获取某一届赛事的所有赛段
 * @param editionId - 届数的 ID
 */
export const fetchStages = async (editionId: number): Promise<ApiEditionStages> => {
  const response = await apiClient.get<ApiEditionStages>(`/editions/${editionId}/stages`)
  return response.data
}

/**
 * 获取某一赛段的完整成绩单
 * @param stageId - 赛段的 ID
 */
export const fetchResults = async (stageId: number): Promise<ApiStageResults> => {
  const response = await apiClient.get<ApiStageResults>(`/stages/${stageId}/results`)
  return response.data
}

/**
 * 获取所有车手列表
 */
export const fetchRiders = async (): Promise<Rider[]> => {
  const response = await apiClient.get<Rider[]>('/riders')
  return response.data
}

/**
 * 获取车手详细信息（统计数据）
 * @param riderId - 车手的 ID
 */
export const fetchRiderDetail = async (riderId: number): Promise<ApiRiderDetail> => {
  const response = await apiClient.get<ApiRiderDetail>(`/riders/${riderId}`)
  return response.data
}

/**
 * 获取车手的所有参赛记录
 * @param riderId - 车手的 ID
 */
export const fetchRiderRaces = async (riderId: number): Promise<ApiRiderRaces> => {
  const response = await apiClient.get<ApiRiderRaces>(`/riders/${riderId}/races`)
  return response.data
}

/**
 * 获取车手的所有赛段冠军记录
 * @param riderId - 车手的 ID
 */
export const fetchRiderWins = async (riderId: number): Promise<ApiRiderWins> => {
  const response = await apiClient.get<ApiRiderWins>(`/riders/${riderId}/wins`)
  return response.data
}
