<template>
  <div class="reset-container">
    <div class="reset-card">
      <button @click="goHome" class="btn-back-home" title="返回主页">← 返回主页</button>

      <!-- 重置成功 -->
      <div v-if="resetSuccess" class="status-container success">
        <div class="status-icon">✅</div>
        <h2 class="status-title">密码重置成功！</h2>
        <p class="status-message">您的密码已成功重置，现在可以使用新密码登录了。</p>
        <router-link to="/login" class="btn-primary">立即登录</router-link>
      </div>

      <!-- 无效链接 -->
      <div v-else-if="invalidToken" class="status-container error">
        <div class="status-icon">❌</div>
        <h2 class="status-title">链接无效或已过期</h2>
        <p class="status-message">{{ errorMessage }}</p>
        <div class="action-buttons">
          <router-link to="/forgot-password" class="btn-secondary">重新申请</router-link>
          <router-link to="/login" class="btn-primary">去登录</router-link>
        </div>
      </div>

      <!-- 重置密码表单 -->
      <div v-else>
        <h1 class="reset-title">重置密码</h1>
        <p class="reset-desc">请输入您的新密码</p>

        <form @submit.prevent="handleSubmit" class="reset-form">
          <div class="form-group">
            <label for="password">新密码</label>
            <input
              id="password"
              v-model="password"
              type="password"
              placeholder="请输入新密码 (至少6位)"
              required
              autocomplete="new-password"
            />
            <span v-if="errors.password" class="error-message">{{ errors.password }}</span>
          </div>

          <div class="form-group">
            <label for="confirmPassword">确认新密码</label>
            <input
              id="confirmPassword"
              v-model="confirmPassword"
              type="password"
              placeholder="请再次输入新密码"
              required
              autocomplete="new-password"
            />
            <span v-if="errors.confirmPassword" class="error-message">{{
              errors.confirmPassword
            }}</span>
          </div>

          <div v-if="errors.general" class="error-message general-error">
            {{ errors.general }}
          </div>

          <button type="submit" class="btn-submit" :disabled="isLoading">
            {{ isLoading ? '重置中...' : '重置密码' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import apiService from '@/services/ApiServices'

const router = useRouter()
const route = useRoute()

const isLoading = ref(false)
const resetSuccess = ref(false)
const invalidToken = ref(false)
const errorMessage = ref('')

const password = ref('')
const confirmPassword = ref('')
const token = ref('')

const errors = reactive({
  password: '',
  confirmPassword: '',
  general: '',
})

const goHome = () => {
  router.push('/')
}

onMounted(() => {
  token.value = route.query.token as string
  if (!token.value) {
    invalidToken.value = true
    errorMessage.value = '无效的重置链接，缺少重置令牌。'
  }
})

const validateForm = (): boolean => {
  errors.password = ''
  errors.confirmPassword = ''
  errors.general = ''

  if (password.value.length < 6) {
    errors.password = '密码至少需要 6 个字符'
    return false
  }

  if (password.value !== confirmPassword.value) {
    errors.confirmPassword = '两次输入的密码不一致'
    return false
  }

  return true
}

const handleSubmit = async () => {
  if (!validateForm()) {
    return
  }

  isLoading.value = true
  errors.general = ''

  try {
    await apiService.resetPassword({
      token: token.value,
      new_password: password.value,
    })
    resetSuccess.value = true
  } catch (error: unknown) {
    console.error('重置失败:', error)
    const err = error as { response?: { data?: { detail?: string } } }
    const detail = err.response?.data?.detail || '重置失败，请稍后重试'

    // 检查是否是令牌相关的错误
    if (detail.includes('无效') || detail.includes('过期')) {
      invalidToken.value = true
      errorMessage.value = detail
    } else {
      errors.general = detail
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.reset-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  padding: 20px;
}

.reset-card {
  background: white;
  border-radius: 12px;
  padding: 40px;
  width: 100%;
  max-width: 450px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
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

.reset-title {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  text-align: center;
  margin-bottom: 10px;
}

.reset-desc {
  font-size: 14px;
  color: #666;
  text-align: center;
  margin-bottom: 30px;
}

.reset-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
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
  padding: 14px 16px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 15px;
  transition: border-color 0.3s;
}

.form-group input:focus {
  outline: none;
  border-color: #f5576c;
  box-shadow: 0 0 0 3px rgba(245, 87, 108, 0.1);
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

.btn-submit {
  padding: 14px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(245, 87, 108, 0.4);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 状态页面样式 */
.status-container {
  text-align: center;
  padding: 20px 0;
}

.status-icon {
  font-size: 72px;
  margin-bottom: 20px;
}

.status-title {
  font-size: 24px;
  font-weight: 700;
  color: #333;
  margin-bottom: 15px;
}

.status-message {
  font-size: 15px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 30px;
}

.success .status-title {
  color: #27ae60;
}

.error .status-title {
  color: #e74c3c;
}

.action-buttons {
  display: flex;
  gap: 15px;
  justify-content: center;
}

.btn-primary {
  display: inline-block;
  padding: 14px 40px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  text-decoration: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(245, 87, 108, 0.4);
}

.btn-secondary {
  display: inline-block;
  padding: 14px 40px;
  background: transparent;
  color: #f5576c;
  text-decoration: none;
  border: 2px solid #f5576c;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: #f5576c;
  color: white;
}
</style>
