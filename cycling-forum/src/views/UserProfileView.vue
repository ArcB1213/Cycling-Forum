<template>
  <div class="profile-container">
    <div class="profile-header">
      <button @click="goBack" class="btn-back">← 返回</button>
      <h1>个人中心</h1>
    </div>

    <div class="profile-content">
      <!-- 用户信息卡片 -->
      <div class="info-card">
        <div class="avatar-section">
          <div class="avatar-wrapper" @click="showAvatarModal = true" title="点击查看大图">
            <img :src="getAvatarUrl()" alt="用户头像" class="user-avatar" />
            <div class="avatar-overlay">
              <span>查看大图</span>
            </div>
          </div>
          <div class="user-details">
            <div style="display: flex; align-items: center; gap: 10px">
              <h2>{{ currentUser?.nickname }}</h2>
              <button @click="showNicknameModal = true" class="btn-edit">修改</button>
            </div>
            <p class="user-email">{{ currentUser?.email }}</p>
            <p class="user-date">注册时间: {{ formatDate(currentUser?.created_at) }}</p>
            <span v-if="currentUser?.is_verified" class="badge-verified">✓ 已验证</span>
          </div>
        </div>
      </div>

      <!-- 头像大图模态框 -->
      <div v-if="showAvatarModal" class="modal-overlay" @click="showAvatarModal = false">
        <div class="modal-content" @click.stop>
          <img :src="getAvatarUrl()" alt="头像大图" class="full-avatar" />
          <div class="modal-actions">
            <button @click="triggerFileInput" class="btn-primary" :disabled="isUpdatingAvatar">
              {{ isUpdatingAvatar ? '上传中...' : '修改头像' }}
            </button>
            <button @click="showAvatarModal = false" class="btn-secondary">关闭</button>
          </div>
          <input
            type="file"
            ref="fileInput"
            style="display: none"
            accept="image/*"
            @change="handleAvatarChange"
          />
          <div v-if="avatarError" class="error-message modal-error">{{ avatarError }}</div>
        </div>
      </div>

      <!-- 修改昵称模态框 -->
      <div v-if="showNicknameModal" class="modal-overlay" @click="showNicknameModal = false">
        <div class="modal-content" @click.stop>
          <h3>修改昵称</h3>
          <form @submit.prevent="handleUpdateNickname" class="form">
            <div class="form-group">
              <label for="nickname">新昵称</label>
              <input
                id="nickname"
                v-model="nicknameForm.nickname"
                type="text"
                placeholder="请输入新昵称 (2-50字符)"
                :disabled="isUpdatingNickname"
                minlength="2"
                maxlength="50"
              />
              <span v-if="nicknameError" class="error-message">{{ nicknameError }}</span>
            </div>
            <div class="modal-actions">
              <button
                type="button"
                @click="showNicknameModal = false"
                class="btn-secondary"
                :disabled="isUpdatingNickname"
              >
                取消
              </button>
              <button type="submit" class="btn-primary" :disabled="isUpdatingNickname">
                {{ isUpdatingNickname ? '修改中...' : '保存' }}
              </button>
            </div>
            <div v-if="nicknameSuccess" class="success-message">昵称修改成功！</div>
          </form>
        </div>
      </div>

      <!-- 我的评价 -->
      <div class="action-card">
        <h3>我的车手评价</h3>
        <div v-if="isLoadingRatings" class="loading-state">加载中...</div>
        <div v-else-if="!myRatings || myRatings.data.length === 0" class="empty-state">
          暂无评价记录
        </div>
        <div v-else class="ratings-list">
          <div
            v-for="rating in myRatings.data"
            :key="rating.rating_id"
            class="rating-card"
            @click="goToRider(rating.rider_id)"
          >
            <div class="rating-card-header">
              <span class="rider-name">{{ (rating as any).rider_name || '未知车手' }}</span>
              <span class="rating-stars">{{ getStarRating(rating.score) }}</span>
            </div>
            <p class="rating-comment">{{ rating.comment || '无文字评价' }}</p>
            <span class="rating-time">{{ formatDate(rating.created_at) }}</span>
          </div>

          <!-- 分页 -->
          <div v-if="myRatings.pagination.total_pages > 1" class="pagination">
            <button
              :disabled="!myRatings.pagination.has_prev"
              @click="loadMyRatings(myRatings.pagination.page - 1)"
            >
              上一页
            </button>
            <span
              >第 {{ myRatings.pagination.page }} / {{ myRatings.pagination.total_pages }} 页</span
            >
            <button
              :disabled="!myRatings.pagination.has_next"
              @click="loadMyRatings(myRatings.pagination.page + 1)"
            >
              下一页
            </button>
          </div>
        </div>
      </div>

      <!-- 修改密码 -->
      <div class="action-card">
        <h3>修改密码</h3>
        <form @submit.prevent="handleUpdatePassword" class="form">
          <div class="form-group">
            <label for="old-password">当前密码</label>
            <input
              id="old-password"
              v-model="passwordForm.oldPassword"
              type="password"
              placeholder="请输入当前密码"
              :disabled="isUpdatingPassword"
              autocomplete="current-password"
            />
          </div>
          <div class="form-group">
            <label for="new-password">新密码</label>
            <input
              id="new-password"
              v-model="passwordForm.newPassword"
              type="password"
              placeholder="请输入新密码 (至少6位)"
              :disabled="isUpdatingPassword"
              autocomplete="new-password"
            />
          </div>
          <div class="form-group">
            <label for="confirm-password">确认新密码</label>
            <input
              id="confirm-password"
              v-model="passwordForm.confirmPassword"
              type="password"
              placeholder="请再次输入新密码"
              :disabled="isUpdatingPassword"
              autocomplete="new-password"
            />
          </div>
          <span v-if="passwordError" class="error-message">{{ passwordError }}</span>
          <button type="submit" class="btn-primary" :disabled="isUpdatingPassword">
            {{ isUpdatingPassword ? '修改中...' : '修改密码' }}
          </button>
          <div v-if="passwordSuccess" class="success-message">密码修改成功！</div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import apiService from '@/services/ApiServices'
import type { User, PaginatedRatingsResponse } from '@/interfaces/types'

const router = useRouter()
const currentUser = ref<User | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

const isUpdatingNickname = ref(false)
const isUpdatingPassword = ref(false)
const isUpdatingAvatar = ref(false)
const showAvatarModal = ref(false)
const showNicknameModal = ref(false)

const nicknameError = ref('')
const passwordError = ref('')
const avatarError = ref('')
const nicknameSuccess = ref(false)
const passwordSuccess = ref(false)

// 用户评价数据
const myRatings = ref<PaginatedRatingsResponse | null>(null)
const isLoadingRatings = ref(false)

const nicknameForm = reactive({
  nickname: '',
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

onMounted(async () => {
  const userStr = localStorage.getItem('user')
  if (userStr) {
    currentUser.value = JSON.parse(userStr)
    nicknameForm.nickname = currentUser.value?.nickname || ''
  }

  // 如果没有登录，跳转到登录页
  if (!apiService.isAuthenticated()) {
    router.push('/login')
    return
  }

  // 加载用户评价
  loadMyRatings()
})

const loadMyRatings = async (page = 1) => {
  isLoadingRatings.value = true
  try {
    myRatings.value = await apiService.fetchMyAllRatings(page, 10)
  } catch (error) {
    console.error('加载评价失败:', error)
  } finally {
    isLoadingRatings.value = false
  }
}

const goBack = () => {
  router.back()
}

const goToRider = (riderId: number) => {
  router.push(`/riders/${riderId}`)
}

const getAvatarUrl = () => {
  return apiService.getAvatarUrl(currentUser.value?.avatar)
}

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleAvatarChange = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    avatarError.value = '请选择图片文件'
    return
  }

  // 验证文件大小 (5MB)
  if (file.size > 5 * 1024 * 1024) {
    avatarError.value = '图片大小不能超过 5MB'
    return
  }

  isUpdatingAvatar.value = true
  avatarError.value = ''

  try {
    const updatedUser = await apiService.updateUserAvatar(file)
    currentUser.value = updatedUser
    localStorage.setItem('user', JSON.stringify(updatedUser))
    // 成功后可以关闭模态框或者保持开启
    // showAvatarModal.value = false
  } catch (error: unknown) {
    console.error('修改头像失败:', error)
    const err = error as { response?: { data?: { detail?: string } } }
    avatarError.value = err.response?.data?.detail || '上传失败，请稍后重试'
  } finally {
    isUpdatingAvatar.value = false
    // 清空 input，以便下次选择同一文件也能触发 change
    if (fileInput.value) fileInput.value.value = ''
  }
}

const handleUpdateNickname = async () => {
  nicknameError.value = ''
  nicknameSuccess.value = false

  if (nicknameForm.nickname.length < 2 || nicknameForm.nickname.length > 50) {
    nicknameError.value = '昵称长度需要在 2-50 个字符之间'
    return
  }

  if (nicknameForm.nickname === currentUser.value?.nickname) {
    nicknameError.value = '新昵称与当前昵称相同'
    return
  }

  isUpdatingNickname.value = true

  try {
    const updatedUser = await apiService.updateNickname(nicknameForm.nickname)
    currentUser.value = updatedUser
    localStorage.setItem('user', JSON.stringify(updatedUser))
    nicknameSuccess.value = true
    setTimeout(() => {
      nicknameSuccess.value = false
      showNicknameModal.value = false
    }, 2000)
  } catch (error: unknown) {
    console.error('修改昵称失败:', error)
    const err = error as { response?: { data?: { detail?: string } } }
    nicknameError.value = err.response?.data?.detail || '修改失败，请稍后重试'
  } finally {
    isUpdatingNickname.value = false
  }
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

const getStarRating = (score: number) => {
  return '★'.repeat(score) + '☆'.repeat(5 - score)
}

const handleUpdatePassword = async () => {
  passwordError.value = ''
  passwordSuccess.value = false

  if (!passwordForm.oldPassword) {
    passwordError.value = '请输入当前密码'
    return
  }

  if (passwordForm.newPassword.length < 6) {
    passwordError.value = '新密码至少需要 6 个字符'
    return
  }

  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    passwordError.value = '两次输入的新密码不一致'
    return
  }

  if (passwordForm.oldPassword === passwordForm.newPassword) {
    passwordError.value = '新密码不能与当前密码相同'
    return
  }

  isUpdatingPassword.value = true

  try {
    await apiService.updatePassword(passwordForm.oldPassword, passwordForm.newPassword)
    passwordSuccess.value = true
    // 清空表单
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    setTimeout(() => {
      passwordSuccess.value = false
    }, 3000)
  } catch (error: unknown) {
    console.error('修改密码失败:', error)
    const err = error as { response?: { data?: { detail?: string } } }
    passwordError.value = err.response?.data?.detail || '修改失败，请稍后重试'
  } finally {
    isUpdatingPassword.value = false
  }
}
</script>

<style scoped>
.profile-container {
  min-height: 100vh;
  background: linear-gradient(180deg, #ffed00 70%, black 100%);
}

.profile-header {
  max-width: 800px;
  margin: 0 auto 30px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.btn-back {
  padding: 8px 16px;
  background: white;
  color: #da291c;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-back:hover {
  background: #da291c;
  color: white;
  transform: translateX(-4px);
}

.btn-edit {
  padding: 4px 12px;
  background: #f0f0f0;
  color: #333;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-edit:hover {
  background: #da291c;
  color: white;
}

.profile-header h1 {
  color: rgb(5, 5, 5);
  font-size: 32px;
  font-weight: 700;
  margin: 0;
}

.profile-content {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-card,
.action-card {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.avatar-section {
  display: flex;
  align-items: center;
  gap: 25px;
}

.avatar-wrapper {
  position: relative;
  cursor: pointer;
  border-radius: 50%;
  overflow: hidden;
  width: 200px;
  height: 200px;
  border: 4px solid #ff286e;
  transition: transform 0.3s;
}

.avatar-wrapper:hover {
  transform: scale(1.05);
}

.avatar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
}

.avatar-wrapper:hover .avatar-overlay {
  opacity: 1;
}

.avatar-overlay span {
  color: white;
  font-size: 14px;
  font-weight: 600;
}

.user-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-details h2 {
  font-size: 24px;
  font-weight: 700;
  color: #333;
  margin: 0 0 8px 0;
}

.user-email {
  font-size: 15px;
  color: #666;
  margin: 0 0 4px 0;
}

.user-date {
  font-size: 13px;
  color: #999;
  margin: 0 0 8px 0;
}

.badge-verified {
  display: inline-block;
  padding: 4px 10px;
  background: #27ae60;
  color: white;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.action-card h3 {
  font-size: 20px;
  font-weight: 700;
  color: #333;
  margin: 0 0 20px 0;
  padding-bottom: 15px;
  border-bottom: 2px solid #f0f0f0;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 14px;
  font-weight: 600;
  color: #555;
}

.form-group input {
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 15px;
  transition: border-color 0.3s;
}

.form-group input:focus {
  outline: none;
  border-color: #ff286e;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-group input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.error-message {
  color: #e74c3c;
  font-size: 13px;
  margin-top: 2px;
}

.success-message {
  color: #27ae60;
  font-size: 14px;
  padding: 10px;
  background: #e8f5e9;
  border-radius: 6px;
  text-align: center;
  font-weight: 600;
}

.btn-primary {
  padding: 12px;
  background-color: black;
  color: #ffed00;
  border: none;
  border-radius: 6px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  margin-top: 5px;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
  background: #ffed00;
  color: black;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 12px;
  background-color: #f0f0f0;
  color: #333;
  border: none;
  border-radius: 6px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-secondary:hover {
  background-color: #e0e0e0;
}

/* 模态框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(5px);
}

.modal-content {
  background: white;
  padding: 20px;
  border-radius: 16px;
  max-width: 90%;
  max-height: 90%;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-content h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #333;
}

.full-avatar {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  border-radius: 8px;
}

.modal-actions {
  display: flex;
  gap: 15px;
}

.modal-actions button {
  flex: 1;
}

.modal-error {
  margin-top: -10px;
  text-align: center;
}

/* 评价列表 */
.ratings-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.rating-card {
  padding: 15px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.rating-card:hover {
  background: #eff6ff;
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.rating-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.rider-name {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.rating-stars {
  color: #fbbf24;
  font-size: 14px;
}

.rating-comment {
  color: #475569;
  font-size: 14px;
  margin: 0 0 8px 0;
  line-height: 1.5;
}

.rating-time {
  font-size: 12px;
  color: #94a3b8;
}

.loading-state,
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #94a3b8;
  font-size: 14px;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}

.pagination button {
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s;
}

.pagination button:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #3b82f6;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination span {
  font-size: 14px;
  color: #64748b;
}

@media (max-width: 768px) {
  .avatar-section {
    flex-direction: column;
    text-align: center;
  }

  .profile-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .modal-actions {
    flex-direction: column;
  }
}
</style>
