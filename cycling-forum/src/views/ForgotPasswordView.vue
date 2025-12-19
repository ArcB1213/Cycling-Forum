<template>
  <div class="forgot-container">
    <div class="forgot-card">
      <button @click="goBack" class="btn-back" title="返回登录">← 返回登录</button>

      <!-- 发送成功提示 -->
      <div v-if="emailSent" class="success-container">
        <div class="success-icon">📧</div>
        <h2 class="success-title">邮件已发送</h2>
        <p class="success-message">
          如果该邮箱已注册并验证，我们已向 <strong>{{ email }}</strong> 发送了密码重置邮件。
          请查收邮件并点击链接重置密码。
        </p>
        <div class="success-tips">
          <p>📫 没有收到邮件？</p>
          <ul>
            <li>请检查垃圾邮件文件夹</li>
            <li>确认邮箱地址是否正确</li>
            <li>重置链接有效期为 1 小时</li>
          </ul>
        </div>
        <router-link to="/login" class="btn-primary">返回登录</router-link>
      </div>

      <!-- 忘记密码表单 -->
      <div v-else>
        <h1 class="forgot-title">忘记密码</h1>
        <p class="forgot-desc">请输入您注册时使用的邮箱地址，我们将发送密码重置链接。</p>

        <form @submit.prevent="handleSubmit" class="forgot-form">
          <div class="form-group">
            <label for="email">邮箱地址</label>
            <input
              id="email"
              v-model="email"
              type="email"
              placeholder="请输入您的邮箱"
              required
              autocomplete="email"
            />
            <span v-if="errors.email" class="error-message">{{ errors.email }}</span>
          </div>

          <div v-if="errors.general" class="error-message general-error">
            {{ errors.general }}
          </div>

          <button type="submit" class="btn-submit" :disabled="isLoading">
            {{ isLoading ? '发送中...' : '发送重置邮件' }}
          </button>
        </form>

        <div class="links">
          <router-link to="/login">返回登录</router-link>
          <span class="divider">|</span>
          <router-link to="/register">注册新账号</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import apiService from '@/services/ApiServices'

const router = useRouter()
const isLoading = ref(false)
const emailSent = ref(false)
const email = ref('')

const errors = reactive({
  email: '',
  general: '',
})

const goBack = () => {
  router.push('/login')
}

const validateForm = (): boolean => {
  errors.email = ''
  errors.general = ''

  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
  if (!emailRegex.test(email.value)) {
    errors.email = '请输入有效的邮箱地址'
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
    await apiService.forgotPassword({ email: email.value })
    emailSent.value = true
  } catch (error: unknown) {
    console.error('发送失败:', error)
    const err = error as { response?: { data?: { detail?: string } } }
    errors.general = err.response?.data?.detail || '发送失败，请稍后重试'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.forgot-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.forgot-card {
  background: white;
  border-radius: 12px;
  padding: 40px;
  width: 100%;
  max-width: 450px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.btn-back {
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

.btn-back:hover {
  background: rgba(255, 255, 255, 0.4);
  border-color: white;
  transform: translateX(-4px);
}

.forgot-title {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  text-align: center;
  margin-bottom: 10px;
}

.forgot-desc {
  font-size: 14px;
  color: #666;
  text-align: center;
  margin-bottom: 30px;
  line-height: 1.5;
}

.forgot-form {
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

.btn-submit {
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
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.links {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
}

.links a {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
}

.links a:hover {
  text-decoration: underline;
}

.divider {
  margin: 0 12px;
  color: #ccc;
}

/* 发送成功样式 */
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
  margin: 0 0 0 20px;
  padding: 0;
  color: #666;
  font-size: 14px;
}

.success-tips li {
  margin-bottom: 5px;
}

.btn-primary {
  display: inline-block;
  padding: 14px 40px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}
</style>
