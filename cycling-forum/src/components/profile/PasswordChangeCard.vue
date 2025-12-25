<template>
  <div class="action-card">
    <h3>修改密码</h3>
    <form @submit.prevent="handleSubmit" class="form">
      <div class="form-group">
        <label for="old-password">当前密码</label>
        <input
          id="old-password"
          v-model="formData.oldPassword"
          type="password"
          placeholder="请输入当前密码"
          :disabled="isUpdating"
          autocomplete="current-password"
        />
      </div>
      <div class="form-group">
        <label for="new-password">新密码</label>
        <input
          id="new-password"
          v-model="formData.newPassword"
          type="password"
          placeholder="请输入新密码 (至少6位)"
          :disabled="isUpdating"
          autocomplete="new-password"
        />
      </div>
      <div class="form-group">
        <label for="confirm-password">确认新密码</label>
        <input
          id="confirm-password"
          v-model="formData.confirmPassword"
          type="password"
          placeholder="请再次输入新密码"
          :disabled="isUpdating"
          autocomplete="new-password"
        />
      </div>
      <span v-if="errorMessage" class="error-message">{{ errorMessage }}</span>
      <button type="submit" class="btn-primary" :disabled="isUpdating">
        {{ isUpdating ? '修改中...' : '修改密码' }}
      </button>
      <div v-if="successMessage" class="success-message">{{ successMessage }}</div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import apiService from '@/services/ApiServices'

const emit = defineEmits<{
  success: []
}>()

const formData = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const isUpdating = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const validateForm = (): boolean => {
  errorMessage.value = ''

  if (!formData.oldPassword) {
    errorMessage.value = '请输入当前密码'
    return false
  }

  if (formData.newPassword.length < 6) {
    errorMessage.value = '新密码至少需要 6 个字符'
    return false
  }

  if (formData.newPassword !== formData.confirmPassword) {
    errorMessage.value = '两次输入的新密码不一致'
    return false
  }

  if (formData.oldPassword === formData.newPassword) {
    errorMessage.value = '新密码不能与当前密码相同'
    return false
  }

  return true
}

const handleSubmit = async () => {
  if (!validateForm()) {
    return
  }

  isUpdating.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await apiService.updatePassword(formData.oldPassword, formData.newPassword)
    successMessage.value = '密码修改成功！'
    emit('success')

    // 清空表单
    formData.oldPassword = ''
    formData.newPassword = ''
    formData.confirmPassword = ''

    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  } catch (error: unknown) {
    console.error('修改密码失败:', error)
    const err = error as { response?: { data?: { detail?: string } } }
    errorMessage.value = err.response?.data?.detail || '修改失败，请稍后重试'
  } finally {
    isUpdating.value = false
  }
}
</script>

<style scoped>
.action-card {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
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
</style>
