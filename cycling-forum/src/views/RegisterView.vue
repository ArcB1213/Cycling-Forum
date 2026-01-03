<template>
  <div class="register-container">
    <div class="register-card">
      <button @click="goHome" class="btn-back-home" title="返回主页">← 返回主页</button>

      <!-- 注册成功提示 -->
      <div v-if="registrationSuccess" class="success-container">
        <div class="success-icon">✉️</div>
        <h2 class="success-title">验证邮件已发送！</h2>
        <p class="success-message">
          我们已向 <strong>{{ registeredEmail }}</strong> 发送了一封验证邮件。
          请查收邮件并点击链接完成注册。
        </p>
        <div class="success-tips">
          <p>📫 没有收到邮件？</p>
          <ul>
            <li>请检查垃圾邮件文件夹</li>
            <li>确认邮箱地址是否正确</li>
          </ul>
          <button @click="handleResendEmail" class="btn-resend" :disabled="resendCooldown > 0">
            {{ resendCooldown > 0 ? `${resendCooldown}秒后可重发` : '重新发送验证邮件' }}
          </button>
        </div>
        <router-link to="/login" class="btn-go-login">去登录</router-link>
      </div>

      <!-- 注册表单 -->
      <div v-else>
        <h1 class="register-title">注册账号</h1>
        <form @submit.prevent="handleRegister" class="register-form">
          <div class="form-group">
            <label for="email">邮箱 *</label>
            <input
              id="email"
              v-model="registerForm.email"
              type="email"
              placeholder="请输入邮箱"
              required
              autocomplete="email"
            />
            <span v-if="errors.email" class="error-message">{{ errors.email }}</span>
          </div>

          <div class="form-group">
            <label for="nickname">昵称 *</label>
            <input
              id="nickname"
              v-model="registerForm.nickname"
              type="text"
              placeholder="请输入昵称 (2-50字符)"
              required
              minlength="2"
              maxlength="50"
            />
            <span v-if="errors.nickname" class="error-message">{{ errors.nickname }}</span>
          </div>

          <div class="form-group">
            <label for="password">密码 *</label>
            <input
              id="password"
              v-model="registerForm.password"
              type="password"
              placeholder="请输入密码 (至少6位)"
              required
              autocomplete="new-password"
            />
            <span v-if="errors.password" class="error-message">{{ errors.password }}</span>
          </div>

          <div class="form-group">
            <label for="confirmPassword">确认密码 *</label>
            <input
              id="confirmPassword"
              v-model="confirmPassword"
              type="password"
              placeholder="请再次输入密码"
              required
              autocomplete="new-password"
            />
            <span v-if="errors.confirmPassword" class="error-message">{{
              errors.confirmPassword
            }}</span>
          </div>

          <div class="form-group">
            <label for="avatar">头像 (可选)</label>
            <div class="avatar-upload">
              <div class="avatar-preview">
                <img v-if="avatarPreview" :src="avatarPreview" alt="头像预览" class="preview-img" />
                <div v-else class="preview-placeholder">
                  <span>📷</span>
                  <p>点击选择头像</p>
                </div>
                <input
                  id="avatar"
                  ref="avatarInput"
                  type="file"
                  accept="image/*"
                  style="display: none"
                  @change="handleAvatarChange"
                />
              </div>
              <div class="avatar-info">
                <p v-if="avatarFile" class="file-name">{{ avatarFile.name }}</p>
                <p v-else class="file-hint">支持 JPG、PNG、GIF 等格式，最大 5MB</p>
                <button
                  v-if="!avatarFile"
                  type="button"
                  @click="selectAvatar"
                  class="btn-select-avatar"
                >
                  选择文件
                </button>
                <button v-else type="button" @click="clearAvatar" class="btn-clear-avatar">
                  清除
                </button>
              </div>
            </div>
            <span v-if="errors.avatar" class="error-message">{{ errors.avatar }}</span>
          </div>

          <div v-if="errors.general" class="error-message general-error">
            {{ errors.general }}
          </div>

          <button type="submit" class="btn-register" :disabled="isLoading">
            {{ isLoading ? '注册中...' : '注册' }}
          </button>
        </form>

        <div class="login-link">已有账号？<router-link to="/login">立即登录</router-link></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import apiService from '@/services/ApiServices'
import type { UserRegisterRequest } from '@/interfaces/types'

const router = useRouter()
const route = useRoute()
const isLoading = ref(false)
const confirmPassword = ref('')
const avatarInput = ref<HTMLInputElement>()
const avatarFile = ref<File | null>(null)
const avatarPreview = ref<string>('')

// 注册成功状态
const registrationSuccess = ref(false)
const registeredEmail = ref('')
const resendCooldown = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

const registerForm = reactive<UserRegisterRequest>({
  email: '',
  nickname: '',
  password: '',
  avatar: '',
})

const errors = reactive({
  email: '',
  nickname: '',
  password: '',
  confirmPassword: '',
  avatar: '',
  general: '',
})

const selectAvatar = () => {
  avatarInput.value?.click()
}

const handleAvatarChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  if (!file) return

  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    errors.avatar = '请选择图片文件'
    return
  }

  // 验证文件大小 (5MB)
  if (file.size > 5 * 1024 * 1024) {
    errors.avatar = '文件大小不能超过 5MB'
    return
  }

  errors.avatar = ''
  avatarFile.value = file

  // 创建预览 URL
  const reader = new FileReader()
  reader.onload = (e) => {
    avatarPreview.value = e.target?.result as string
  }
  reader.readAsDataURL(file)
}

const clearAvatar = () => {
  avatarFile.value = null
  avatarPreview.value = ''
  errors.avatar = ''
  if (avatarInput.value) {
    avatarInput.value.value = ''
  }
}

const validateForm = (): boolean => {
  errors.email = ''
  errors.nickname = ''
  errors.password = ''
  errors.confirmPassword = ''
  errors.general = ''

  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
  if (!emailRegex.test(registerForm.email)) {
    errors.email = '请输入有效的邮箱地址'
    return false
  }

  if (registerForm.nickname.length < 2 || registerForm.nickname.length > 50) {
    errors.nickname = '昵称长度需要在 2-50 个字符之间'
    return false
  }

  if (registerForm.password.length < 6) {
    errors.password = '密码至少需要 6 个字符'
    return false
  }

  if (registerForm.password !== confirmPassword.value) {
    errors.confirmPassword = '两次输入的密码不一致'
    return false
  }

  return true
}

const handleRegister = async () => {
  if (!validateForm()) {
    return
  }

  isLoading.value = true
  errors.general = ''

  try {
    // 上传头像文件或使用默认头像
    if (avatarFile.value) {
      // 如果选择了文件，上传到服务器
      const avatarUrl = await apiService.uploadAvatar(avatarFile.value)
      registerForm.avatar = avatarUrl
    } else if (!registerForm.avatar) {
      // 如果没有选择文件且没有 URL，使用默认头像标识
      registerForm.avatar = 'default'
    }

    const response = await apiService.register(registerForm)

    // 注册成功，显示验证邮件提示
    registrationSuccess.value = true
    registeredEmail.value = response.email
    startResendCooldown()
  } catch (error: unknown) {
    console.error('注册失败:', error)
    const err = error as { response?: { data?: { detail?: string } } }
    errors.general = err.response?.data?.detail || '注册失败，请稍后重试'
  } finally {
    isLoading.value = false
  }
}

// 重发验证邮件冷却计时
const startResendCooldown = () => {
  resendCooldown.value = 60
  cooldownTimer = setInterval(() => {
    resendCooldown.value--
    if (resendCooldown.value <= 0) {
      if (cooldownTimer) {
        clearInterval(cooldownTimer)
        cooldownTimer = null
      }
    }
  }, 1000)
}

// 重新发送验证邮件
const handleResendEmail = async () => {
  if (resendCooldown.value > 0) return

  try {
    await apiService.resendVerificationEmail(registeredEmail.value)
    startResendCooldown()
    alert('验证邮件已重新发送，请查收。')
  } catch (error: unknown) {
    console.error('重发邮件失败:', error)
    const err = error as { response?: { data?: { detail?: string } } }
    alert(err.response?.data?.detail || '发送失败，请稍后重试')
  }
}

// 清理定时器
onUnmounted(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
  }
})

const goHome = () => {
  router.push('/')
}
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(180deg, #ffed00 70%, black 100%);
  padding: 20px;
}

.register-card {
  background: white;
  border-radius: 12px;
  padding: 40px;
  width: 100%;
  max-width: 480px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  max-height: 90vh;
  overflow-y: auto;
}

.register-title {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  text-align: center;
  margin-bottom: 30px;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
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
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.error-message {
  color: #e74c3c;
  font-size: 13px;
  margin-top: 2px;
}

.general-error {
  text-align: center;
  padding: 10px;
  background: #fee;
  border-radius: 6px;
}

.btn-register {
  padding: 14px;
  background: #00ccff;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
  margin-top: 10px;
}

.btn-register:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.btn-register:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-link {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: #666666;
}

.login-link a {
  color: #05aa15;
  text-decoration: none;
  font-weight: 600;
  margin-left: 4px;
}

.login-link a:hover {
  text-decoration: underline;
}

.btn-back-home {
  position: absolute;
  top: 50px;
  left: 20px;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-back-home:hover {
  background: rgba(3, 3, 3, 1);
  border-color: white;
  transform: translateX(-4px);
}

/* 头像上传样式 */
.avatar-upload {
  display: flex;
  gap: 15px;
  align-items: flex-start;
}

.avatar-preview {
  position: relative;
  width: 100px;
  height: 100px;
  border: 2px dashed #00ccff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
  background: #f8f9fa;
  transition: all 0.3s;
  flex-shrink: 0;
}

.avatar-preview:hover {
  border-color: #082dd1;
  background: #f0f2f8;
}

.preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 12px;
}

.preview-placeholder span {
  font-size: 32px;
  margin-bottom: 4px;
}

.avatar-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-name {
  font-size: 13px;
  color: #555;
  word-break: break-all;
  margin: 0;
}

.file-hint {
  font-size: 12px;
  color: #999;
  margin: 0;
}

.btn-select-avatar,
.btn-clear-avatar {
  padding: 8px 16px;
  background: #00ccff;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.3s;
  align-self: flex-start;
}

.btn-select-avatar:hover {
  background: #082dd1;
}

.btn-clear-avatar {
  background: #e74c3c;
}

.btn-clear-avatar:hover {
  background: #c0392b;
}

/* 注册成功提示样式 */
.success-container {
  text-align: center;
  padding: 20px 0;
}

.success-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.success-title {
  font-size: 24px;
  font-weight: 700;
  color: #333;
  margin-bottom: 15px;
}

.success-message {
  font-size: 15px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 25px;
}

.success-message strong {
  color: #667eea;
}

.success-tips {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 25px;
  text-align: left;
}

.success-tips p {
  font-weight: 600;
  color: #555;
  margin-bottom: 10px;
}

.success-tips ul {
  margin: 0 0 15px 20px;
  padding: 0;
  color: #666;
  font-size: 14px;
}

.success-tips li {
  margin-bottom: 5px;
}

.btn-resend {
  width: 100%;
  padding: 12px;
  background: #f0f2f8;
  background: #00ccff;
  border: 1px solid #667eea;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-resend:hover:not(:disabled) {
  background: #667eea;
  color: white;
}

.btn-resend:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  border-color: #ccc;
  color: #999;
}

.btn-go-login {
  display: inline-block;
  padding: 14px 40px;
  color: #00ccff;
  text-decoration: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.btn-go-login:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}
</style>
