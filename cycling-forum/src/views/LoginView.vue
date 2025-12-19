<template>
  <div class="login-container">
    <div class="login-card">
      <button @click="goHome" class="btn-back-home" title="返回主页">← 返回主页</button>
      <h1 class="login-title">登录</h1>

      <!-- 未验证邮箱提示 -->
      <div v-if="showUnverifiedTip" class="unverified-tip">
        <p>📧 您的邮箱尚未验证</p>
        <p>请查收验证邮件并点击链接完成验证。</p>
        <button @click="handleResendVerification" class="btn-resend" :disabled="resendCooldown > 0">
          {{ resendCooldown > 0 ? `${resendCooldown}秒后可重发` : '重新发送验证邮件' }}
        </button>
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="email">邮箱</label>
          <input
            id="email"
            v-model="loginForm.email"
            type="email"
            placeholder="请输入邮箱"
            required
            autocomplete="email"
          />
          <span v-if="errors.email" class="error-message">{{ errors.email }}</span>
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            required
            autocomplete="current-password"
          />
          <span v-if="errors.password" class="error-message">{{ errors.password }}</span>
        </div>

        <div class="forgot-password">
          <router-link to="/forgot-password">忘记密码？</router-link>
        </div>

        <div v-if="errors.general" class="error-message general-error">
          {{ errors.general }}
        </div>

        <button type="submit" class="btn-login" :disabled="isLoading">
          {{ isLoading ? '登录中...' : '登录' }}
        </button>
      </form>

      <div class="register-link">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import apiService from '@/services/ApiServices'
import type { UserLoginRequest } from '@/interfaces/types'

const router = useRouter()
const route = useRoute()
const isLoading = ref(false)
const showUnverifiedTip = ref(false)
const resendCooldown = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

const loginForm = reactive<UserLoginRequest>({
  email: '',
  password: '',
})

const errors = reactive({
  email: '',
  password: '',
  general: '',
})

const validateForm = (): boolean => {
  errors.email = ''
  errors.password = ''
  errors.general = ''
  showUnverifiedTip.value = false

  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
  if (!emailRegex.test(loginForm.email)) {
    errors.email = '请输入有效的邮箱地址'
    return false
  }

  if (loginForm.password.length < 6) {
    errors.password = '密码至少需要 6 个字符'
    return false
  }

  return true
}

const handleLogin = async () => {
  if (!validateForm()) {
    return
  }

  isLoading.value = true
  errors.general = ''

  try {
    const response = await apiService.login(loginForm)

    // 存储 Token 和用户信息
    localStorage.setItem('access_token', response.access_token)
    localStorage.setItem('refresh_token', response.refresh_token)
    localStorage.setItem('user', JSON.stringify(response.user))

    // 跳转到原来想访问的页面，如果没有则跳转到主页
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (error: unknown) {
    console.error('登录失败:', error)
    const err = error as { response?: { data?: { detail?: string }; status?: number } }
    const detail = err.response?.data?.detail || '登录失败，请检查邮箱和密码'

    // 检查是否是未验证邮箱的错误 (403)
    if (err.response?.status === 403 && detail.includes('验证')) {
      showUnverifiedTip.value = true
      errors.general = ''
    } else {
      errors.general = detail
    }
  } finally {
    isLoading.value = false
  }
}

// 重发验证邮件
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

const handleResendVerification = async () => {
  if (resendCooldown.value > 0) return

  try {
    await apiService.resendVerificationEmail(loginForm.email)
    startResendCooldown()
    alert('验证邮件已发送，请查收。')
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
.login-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  background: white;
  border-radius: 12px;
  padding: 40px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.login-title {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  text-align: center;
  margin-bottom: 30px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
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
  margin-top: 4px;
}

.general-error {
  text-align: center;
  padding: 10px;
  background: #fee;
  border-radius: 6px;
  margin-top: -10px;
}

.btn-login {
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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

.btn-login:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.btn-login:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.register-link {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: #666;
}

.register-link a {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
  margin-left: 4px;
}

.register-link a:hover {
  text-decoration: underline;
}

.btn-back-home {
  position: absolute;
  top: 50px;
  left: 20px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-back-home:hover {
  background: rgba(255, 255, 255, 0.4);
  border-color: white;
  transform: translateX(-4px);
}

/* 忘记密码链接 */
.forgot-password {
  text-align: right;
  margin-top: -10px;
}

.forgot-password a {
  color: #667eea;
  text-decoration: none;
  font-size: 13px;
}

.forgot-password a:hover {
  text-decoration: underline;
}

/* 未验证邮箱提示 */
.unverified-tip {
  background: #fff8e6;
  border: 1px solid #ffc107;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
  text-align: center;
}

.unverified-tip p {
  margin: 0 0 8px 0;
  color: #856404;
  font-size: 14px;
}

.unverified-tip p:first-child {
  font-weight: 600;
}

.btn-resend {
  margin-top: 10px;
  padding: 8px 20px;
  background: #ffc107;
  color: #212529;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-resend:hover:not(:disabled) {
  background: #e0a800;
}

.btn-resend:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
