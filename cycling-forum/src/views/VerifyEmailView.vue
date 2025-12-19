<template>
  <div class="verify-container">
    <div class="verify-card">
      <button @click="goHome" class="btn-back-home" title="返回主页">← 返回主页</button>

      <!-- 验证中 -->
      <div v-if="isLoading" class="status-container">
        <div class="loading-spinner"></div>
        <h2 class="status-title">正在验证邮箱...</h2>
        <p class="status-message">请稍候，我们正在验证您的邮箱地址。</p>
      </div>

      <!-- 验证成功 -->
      <div v-else-if="verifySuccess" class="status-container success">
        <div class="status-icon">✅</div>
        <h2 class="status-title">邮箱验证成功！</h2>
        <p class="status-message">{{ message }}</p>
        <router-link to="/login" class="btn-primary">立即登录</router-link>
      </div>

      <!-- 验证失败 -->
      <div v-else class="status-container error">
        <div class="status-icon">❌</div>
        <h2 class="status-title">验证失败</h2>
        <p class="status-message">{{ errorMessage }}</p>
        <div class="action-buttons">
          <router-link to="/register" class="btn-secondary">重新注册</router-link>
          <router-link to="/login" class="btn-primary">去登录</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import apiService from '@/services/ApiServices'

const router = useRouter()
const route = useRoute()

const isLoading = ref(true)
const verifySuccess = ref(false)
const message = ref('')
const errorMessage = ref('')

const goHome = () => {
  router.push('/')
}

onMounted(async () => {
  const token = route.query.token as string

  if (!token) {
    isLoading.value = false
    errorMessage.value = '无效的验证链接，缺少验证令牌。'
    return
  }

  try {
    const response = await apiService.verifyEmail(token)
    verifySuccess.value = true
    message.value = response.message
  } catch (error: unknown) {
    console.error('验证失败:', error)
    const err = error as { response?: { data?: { detail?: string } } }
    errorMessage.value = err.response?.data?.detail || '验证失败，请稍后重试或重新注册。'
  } finally {
    isLoading.value = false
  }
})
</script>

<style scoped>
.verify-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.verify-card {
  background: white;
  border-radius: 12px;
  padding: 50px 40px;
  width: 100%;
  max-width: 480px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  text-align: center;
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

.status-container {
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

.loading-spinner {
  width: 60px;
  height: 60px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.action-buttons {
  display: flex;
  gap: 15px;
  justify-content: center;
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

.btn-secondary {
  display: inline-block;
  padding: 14px 40px;
  background: transparent;
  color: #667eea;
  text-decoration: none;
  border: 2px solid #667eea;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: #667eea;
  color: white;
}

.success .status-title {
  color: #27ae60;
}

.error .status-title {
  color: #e74c3c;
}
</style>
