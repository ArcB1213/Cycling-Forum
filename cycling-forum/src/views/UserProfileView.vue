<template>
  <div class="profile-container">
    <div class="profile-header">
      <button @click="goBack" class="btn-back">← 返回</button>
      <h1>{{ isOwner ? '个人中心' : '用户主页' }}</h1>
    </div>

    <div v-if="isLoadingUser" class="loading-container">加载中...</div>

    <div v-else-if="userError" class="error-container">{{ userError }}</div>

    <div v-else class="profile-content">
      <!-- 用户信息卡片 -->
      <UserInfoCard
        :user="profileUser"
        :is-owner="isOwner"
        @edit-nickname="showNicknameModal = true"
        @edit-avatar="showAvatarModal = true"
      />

      <!-- 头像大图模态框 (仅本人可见) -->
      <div v-if="showAvatarModal && isOwner" class="modal-overlay" @click="showAvatarModal = false">
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

      <!-- 修改昵称模态框 (仅本人可见) -->
      <div v-if="showNicknameModal && isOwner" class="modal-overlay" @click="showNicknameModal = false">
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

      <!-- 我的活动 (选项卡) -->
      <UserActivityTabs
        :active-tab="activeTab"
        :is-owner="isOwner"
        @switch-tab="switchTab"
      >
        <!-- 评价列表 -->
        <UserRatingsList
          :active-tab="activeTab"
          :ratings="ratings"
          :is-loading="isLoadingRatings"
          :is-owner="isOwner"
          @go-to-rider="goToRider"
          @load-page="loadRatingsPage"
        />

        <!-- 帖子列表 -->
        <UserPostsList
          :active-tab="activeTab"
          :posts="posts"
          :is-loading="isLoadingPosts"
          :is-owner="isOwner"
          @go-to-post="goToPost"
          @load-page="loadPostsPage"
        />
      </UserActivityTabs>

      <!-- 修改密码 (仅本人可见) -->
      <PasswordChangeCard v-if="isOwner" @success="handlePasswordSuccess" />

      <!-- 注销账号卡片 (仅本人可见) -->
      <div v-if="isOwner" class="action-card danger-card">
        <h3>⚠️ 注销账号</h3>
        <p class="warning-text">
          注销后无法恢复，所有数据（评分、帖子、评论）将被永久删除
        </p>
        <button
          @click="handleDeleteAccount"
          class="btn-danger"
          :disabled="isDeleting"
        >
          {{ isDeleting ? '注销中...' : '注销账号' }}
        </button>
        <div v-if="deleteError" class="error-message">{{ deleteError }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import apiService, { getAvatarUrl as apiGetAvatarUrl } from '@/services/ApiServices'
import type {
  User,
  PaginatedRatingsResponse,
  PaginatedForumPostsResponse,
} from '@/interfaces/types'
import UserInfoCard from '@/components/profile/UserInfoCard.vue'
import UserActivityTabs from '@/components/profile/UserActivityTabs.vue'
import UserRatingsList from '@/components/profile/UserRatingsList.vue'
import UserPostsList from '@/components/profile/UserPostsList.vue'
import PasswordChangeCard from '@/components/profile/PasswordChangeCard.vue'

const router = useRouter()
const route = useRoute()

// 当前登录用户
const currentUser = ref<User | null>(null)
// 要展示的用户（可能是自己，也可能是访客）
const profileUser = ref<User | null>(null)

// 目标用户ID
const targetUserId = computed(() => {
  const userId = route.params.userId as string | undefined
  if (userId) {
    return Number(userId)
  }
  return currentUser.value?.user_id
})

// 是否为本人
const isOwner = computed(() => {
  // 如果没有路由参数，说明访问的是 /profile，显示本人主页
  if (!route.params.userId) {
    return true
  }
  // 有路由参数，判断是否与当前登录用户相同
  return currentUser.value?.user_id === targetUserId.value
})

// 加载状态
const isLoadingUser = ref(false)
const userError = ref('')

const fileInput = ref<HTMLInputElement | null>(null)
const isUpdatingNickname = ref(false)
const isUpdatingAvatar = ref(false)
const showAvatarModal = ref(false)
const showNicknameModal = ref(false)

const nicknameError = ref('')
const avatarError = ref('')
const nicknameSuccess = ref(false)

// 账号删除相关
const isDeleting = ref(false)
const deleteError = ref('')

// 用户评价数据
const ratings = ref<PaginatedRatingsResponse | null>(null)
const isLoadingRatings = ref(false)

// 用户帖子数据
const posts = ref<PaginatedForumPostsResponse | null>(null)
const isLoadingPosts = ref(false)

// 选项卡状态：'ratings' 或 'posts'
const activeTab = ref<'ratings' | 'posts'>('ratings')

const nicknameForm = reactive({
  nickname: '',
})

onMounted(async () => {
  // 加载当前登录用户
  const userStr = localStorage.getItem('user')
  if (userStr) {
    currentUser.value = JSON.parse(userStr)
  }

  // 如果没有登录，跳转到登录页
  if (!apiService.isAuthenticated()) {
    router.push('/login')
    return
  }

  // 加载目标用户信息
  await loadProfileUser()

  // 如果是本人，初始化昵称表单
  if (isOwner.value && currentUser.value) {
    nicknameForm.nickname = currentUser.value.nickname || ''
  }

  // 加载用户评价
  loadRatings()
})

const loadProfileUser = async () => {
  isLoadingUser.value = true
  userError.value = ''

  try {
    if (isOwner.value) {
      // 本人模式：使用当前登录用户信息
      profileUser.value = currentUser.value
    } else {
      // 访客模式：从API获取目标用户信息
      profileUser.value = await apiService.fetchUserById(targetUserId.value!)
    }
  } catch (error: unknown) {
    console.error('加载用户信息失败:', error)
    const err = error as { response?: { status?: number; data?: { detail?: string } } }
    if (err.response?.status === 404) {
      userError.value = '用户不存在'
    } else {
      userError.value = err.response?.data?.detail || '加载失败'
    }
  } finally {
    isLoadingUser.value = false
  }
}

const loadRatings = async (page = 1) => {
  isLoadingRatings.value = true
  try {
    if (isOwner.value) {
      ratings.value = await apiService.fetchMyAllRatings(page, 10)
    } else {
      ratings.value = await apiService.fetchUserRatings(targetUserId.value!, page, 10)
    }
  } catch (error) {
    console.error('加载评价失败:', error)
  } finally {
    isLoadingRatings.value = false
  }
}

const loadPosts = async (page = 1) => {
  isLoadingPosts.value = true
  try {
    if (isOwner.value) {
      posts.value = await apiService.fetchMyForumPosts(page, 10)
    } else {
      posts.value = await apiService.fetchUserPosts(targetUserId.value!, page, 10)
    }
  } catch (error) {
    console.error('加载帖子失败:', error)
  } finally {
    isLoadingPosts.value = false
  }
}

const loadRatingsPage = (page: number) => {
  loadRatings(page)
}

const loadPostsPage = (page: number) => {
  loadPosts(page)
}

const switchTab = (tab: 'ratings' | 'posts') => {
  activeTab.value = tab
  if (tab === 'posts' && !posts.value) {
    loadPosts()
  }
}

const goToPost = (postId: number) => {
  router.push(`/forum/post/${postId}`)
}

const goBack = () => {
  router.back()
}

const goToRider = (riderId: number) => {
  router.push(`/riders/${riderId}`)
}

const getAvatarUrl = () => {
  return apiGetAvatarUrl(profileUser.value?.avatar)
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
    profileUser.value = updatedUser
    localStorage.setItem('user', JSON.stringify(updatedUser))
  } catch (error: unknown) {
    console.error('修改头像失败:', error)
    const err = error as { response?: { data?: { detail?: string } } }
    avatarError.value = err.response?.data?.detail || '上传失败，请稍后重试'
  } finally {
    isUpdatingAvatar.value = false
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

  if (nicknameForm.nickname === profileUser.value?.nickname) {
    nicknameError.value = '新昵称与当前昵称相同'
    return
  }

  isUpdatingNickname.value = true

  try {
    const updatedUser = await apiService.updateNickname(nicknameForm.nickname)
    currentUser.value = updatedUser
    profileUser.value = updatedUser
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

const handlePasswordSuccess = () => {
  // 密码修改成功的回调（可选）
  console.log('密码修改成功')
}

const handleDeleteAccount = async () => {
  // 第一次确认
  if (!confirm('确定要注销账号吗？')) return

  // 第二次确认
  if (!confirm('注销后无法恢复，所有数据（评分、帖子、评论）将被永久删除！确定继续吗？')) return

  isDeleting.value = true
  deleteError.value = ''

  try {
    await apiService.deleteUserAccount()

    // 清除本地存储
    localStorage.removeItem('user')
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')

    alert('账号已成功注销')
    router.push('/login')
  } catch (error: unknown) {
    console.error('注销失败:', error)
    const err = error as { response?: { data?: { detail?: string } } }
    deleteError.value = err.response?.data?.detail || '注销失败，请稍后重试'
  } finally {
    isDeleting.value = false
  }
}

// 监听路由参数变化，当 userId 改变时重新加载数据
watch(
  () => route.params.userId,
  async () => {
    // 重新加载用户信息
    await loadProfileUser()

    // 重新加载评价和帖子
    activeTab.value = 'ratings'
    loadRatings()
    posts.value = null // 清空帖子数据，切换到评价 tab 时才会加载
  }
)
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
  padding-bottom: 40px;
}

.loading-container,
.error-container {
  max-width: 800px;
  margin: 40px auto;
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 12px;
  font-size: 16px;
  color: #666;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.error-container {
  color: #e74c3c;
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

/* 注销账号卡片样式 */
.danger-card {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  border: 2px solid #fecaca;
}

.danger-card h3 {
  font-size: 20px;
  font-weight: 700;
  color: #dc2626;
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.warning-text {
  font-size: 14px;
  color: #dc2626;
  margin-bottom: 20px;
  line-height: 1.6;
}

.btn-danger {
  width: 100%;
  padding: 12px;
  background: #dc2626;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-danger:hover:not(:disabled) {
  background: #b91c1c;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(220, 38, 38, 0.4);
}

.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .profile-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .modal-actions {
    flex-direction: column;
  }
}
</style>
