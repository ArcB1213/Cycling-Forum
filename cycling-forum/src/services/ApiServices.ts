import axios from 'axios'
import type {
  Race,
  ApiRaceEditions,
  ApiEditionStages,
  ApiRiderDetail,
  ApiRiderRaces,
  ApiRiderWins,
  UserRegisterRequest,
  UserLoginRequest,
  TokenResponse,
  User,
  RegisterResponse,
  MessageResponse,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  PaginatedRidersResponse,
  PaginatedStageResultsResponse,
} from '@/interfaces/types' // 导入类型

// FastAPI 后端地址（uvicorn 默认端口 8000）
const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：自动附加 JWT Token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    console.log('Request interceptor - Token:', token ? 'exists' : 'not found')
    if (token) {
      // 确保 headers 对象存在
      config.headers = config.headers || {}
      config.headers['Authorization'] = `Bearer ${token}`
      console.log('Authorization header set:', config.headers['Authorization'])
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

// 响应拦截器：处理 Token 过期
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // 如果是 401 错误且还没有重试过
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          // 尝试刷新 Token
          const response = await axios.post<TokenResponse>(
            'http://127.0.0.1:8000/api/auth/refresh',
            { refresh_token: refreshToken },
          )

          const { access_token, refresh_token: newRefreshToken, user } = response.data

          // 更新存储的 Token
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', newRefreshToken)
          localStorage.setItem('user', JSON.stringify(user))

          // 重新发送原始请求
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        // 刷新失败，清除所有认证信息
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')

        // 跳转到登录页
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  },
)

/**
 * 获取所有赛事
 */
export const fetchRaces = async (): Promise<Race[]> => {
  const response = await apiClient.get<Race[]>('/async/races')
  return response.data
}

/**
 * 获取某一赛事的所有届数 (年份)
 * @param raceId - 赛事的 ID
 */
export const fetchEditions = async (raceId: number): Promise<ApiRaceEditions> => {
  const response = await apiClient.get<ApiRaceEditions>(`/async/races/${raceId}/editions`)
  return response.data
}

/**
 * 获取某一届赛事的所有赛段
 * @param editionId - 届数的 ID
 */
export const fetchStages = async (editionId: number): Promise<ApiEditionStages> => {
  const response = await apiClient.get<ApiEditionStages>(`/async/editions/${editionId}/stages`)
  return response.data
}

/**
 * 获取某一赛段的完整成绩单（分页）
 * @param stageId - 赛段的 ID
 * @param page - 页码，默认为1
 * @param limit - 每页数量，默认为20
 */
export const fetchResults = async (
  stageId: number,
  page: number = 1,
  limit: number = 20,
): Promise<PaginatedStageResultsResponse> => {
  const response = await apiClient.get<PaginatedStageResultsResponse>(
    `/async/stages/${stageId}/results`,
    {
      params: { page, limit },
    },
  )
  return response.data
}

/**
 * 获取所有车手列表（分页）
 * @param page - 页码，默认为1
 * @param limit - 每页数量，默认为16
 */
export const fetchRiders = async (
  page: number = 1,
  limit: number = 18,
  search?: string,
): Promise<PaginatedRidersResponse> => {
  const params: any = { page, limit }
  if (search) {
    params.search = search
  }
  const response = await apiClient.get<PaginatedRidersResponse>('/async/riders', {
    params,
  })
  return response.data
}

/**
 * 获取车手详细信息（统计数据）
 * @param riderId - 车手的 ID
 */
export const fetchRiderDetail = async (riderId: number): Promise<ApiRiderDetail> => {
  const response = await apiClient.get<ApiRiderDetail>(`/async/riders/${riderId}`)
  return response.data
}

/**
 * 获取车手的所有参赛记录
 * @param riderId - 车手的 ID
 */
export const fetchRiderRaces = async (riderId: number): Promise<ApiRiderRaces> => {
  const response = await apiClient.get<ApiRiderRaces>(`/async/riders/${riderId}/races`)
  return response.data
}

/**
 * 获取车手的所有赛段冠军记录
 * @param riderId - 车手的 ID
 */
export const fetchRiderWins = async (riderId: number): Promise<ApiRiderWins> => {
  const response = await apiClient.get<ApiRiderWins>(`/async/riders/${riderId}/wins`)
  return response.data
}

// ============ 认证相关 API ============

/**
 * 用户注册（注册后需要邮箱验证）
 * @param userData - 注册信息
 */
export const register = async (userData: UserRegisterRequest): Promise<RegisterResponse> => {
  const response = await apiClient.post<RegisterResponse>('/async/auth/register', userData)
  return response.data
}

/**
 * 验证邮箱
 * @param token - 验证令牌
 */
export const verifyEmail = async (token: string): Promise<MessageResponse> => {
  const response = await apiClient.post<MessageResponse>('/async/auth/verify-email', { token })
  return response.data
}

/**
 * 重新发送验证邮件
 * @param email - 邮箱地址
 */
export const resendVerificationEmail = async (email: string): Promise<MessageResponse> => {
  const response = await apiClient.post<MessageResponse>('/auth/resend-verification', { email })
  return response.data
}

/**
 * 发送密码重置邮件
 * @param data - 忘记密码请求
 */
export const forgotPassword = async (data: ForgotPasswordRequest): Promise<MessageResponse> => {
  const response = await apiClient.post<MessageResponse>('/auth/forgot-password', data)
  return response.data
}

/**
 * 重置密码
 * @param data - 重置密码请求
 */
export const resetPassword = async (data: ResetPasswordRequest): Promise<MessageResponse> => {
  const response = await apiClient.post<MessageResponse>('/auth/reset-password', data)
  return response.data
}

/**
 * 用户登录
 * @param loginData - 登录信息
 */
export const login = async (loginData: UserLoginRequest): Promise<TokenResponse> => {
  const response = await apiClient.post<TokenResponse>('/async/auth/login', loginData)
  return response.data
}

/**
 * 获取当前用户信息
 */
export const getCurrentUser = async (): Promise<User> => {
  const response = await apiClient.get<User>('/auth/me')
  return response.data
}

/**
 * 修改昵称
 * @param nickname - 新昵称
 */
export const updateNickname = async (nickname: string): Promise<User> => {
  const response = await apiClient.put<User>('/auth/update-nickname', { nickname })
  return response.data
}

/**
 * 修改密码
 * @param oldPassword - 当前密码
 * @param newPassword - 新密码
 */
export const updatePassword = async (
  oldPassword: string,
  newPassword: string,
): Promise<MessageResponse> => {
  const response = await apiClient.put<MessageResponse>('/auth/update-password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
  return response.data
}

/**
 * 获取论坛帖子列表（需要登录）
 */
export const getForumPosts = async (): Promise<{
  message: string
  user: User
  posts: Array<{ id: number; title: string; author: string; content: string }>
}> => {
  const response = await apiClient.get('/forum/posts')
  return response.data
}

/**
 * 上传头像文件
 * @param file - 图片文件
 */
export const uploadAvatar = async (file: File): Promise<string> => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiClient.post<{ avatar_url: string }>('/upload/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data.avatar_url
}

/**
 * 上传并更新当前用户头像
 * @param file - 图片文件
 */
export const updateUserAvatar = async (file: File): Promise<User> => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiClient.post<User>('/auth/update-avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

/**
 * 检查用户是否已登录
 */
export const isAuthenticated = (): boolean => {
  return !!localStorage.getItem('access_token')
}

/**
 * 退出登录
 */
export const logout = (): void => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
}

/**
 * 获取完整的头像 URL
 * @param avatar - 头像路径或标识
 */
export const getAvatarUrl = (avatar?: string): string => {
  // 默认头像
  if (!avatar || avatar === 'default') {
    return '/src/assets/default.jpg'
  }
  // 如果是相对路径，转换为完整的后端 URL
  if (avatar.startsWith('/uploads')) {
    return `http://127.0.0.1:8000${avatar}`
  }
  // 如果已经是完整 URL，直接返回
  return avatar
}

// 默认导出所有 API 方法
export default {
  fetchRaces,
  fetchEditions,
  fetchStages,
  fetchResults,
  fetchRiders,
  fetchRiderDetail,
  fetchRiderRaces,
  fetchRiderWins,
  register,
  verifyEmail,
  resendVerificationEmail,
  forgotPassword,
  resetPassword,
  login,
  getCurrentUser,
  updateNickname,
  updatePassword,
  getForumPosts,
  uploadAvatar,
  updateUserAvatar,
  isAuthenticated,
  logout,
  getAvatarUrl,
}
