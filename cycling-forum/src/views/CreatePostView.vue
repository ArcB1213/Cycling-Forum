<template>
  <div class="create-post-container">
    <div class="create-post-header">
      <h1>发布新帖</h1>
      <button @click="goBack" class="btn-back">返回</button>
    </div>

    <div class="create-post-form">
      <div v-if="error" class="error-box">
        {{ error }}
      </div>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="title">标题 *</label>
          <input
            id="title"
            v-model="formData.title"
            type="text"
            placeholder="请输入帖子标题（5-200 字）"
            minlength="5"
            maxlength="200"
            required
          />
        </div>

        <div class="form-group">
          <label for="content">正文 *</label>
          <textarea
            id="content"
            v-model="formData.content"
            placeholder="请输入帖子内容（10-10000 字）"
            minlength="10"
            maxlength="10000"
            rows="12"
            required
          ></textarea>
          <div class="char-count">{{ formData.content.length }} / 10000</div>
        </div>

        <div class="form-actions">
          <button type="submit" :disabled="isSubmitting" class="btn-submit">
            {{ isSubmitting ? '发布中...' : '发布帖子' }}
          </button>
          <button type="button" @click="goBack" class="btn-cancel">取消</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import apiService, { createForumPost } from '@/services/ApiServices'
import type { ForumPostCreate } from '@/interfaces/types'

const router = useRouter()
const isSubmitting = ref(false)
const error = ref('')

const formData = reactive<ForumPostCreate>({
  title: '',
  content: ''
})

const handleSubmit = async () => {
  error.value = ''

  // 验证
  if (formData.title.trim().length < 5) {
    error.value = '标题至少需要 5 个字符'
    return
  }
  if (formData.content.trim().length < 10) {
    error.value = '正文至少需要 10 个字符'
    return
  }

  isSubmitting.value = true

  try {
    const newPost = await createForumPost({
      title: formData.title.trim(),
      content: formData.content.trim()
    })
    // 跳转到帖子详情
    router.push(`/forum/post/${newPost.post_id}`)
  } catch (err: unknown) {
    console.error('发帖失败:', err)
    const error_obj = err as { response?: { data?: { detail?: string } } }
    error.value = error_obj.response?.data?.detail || '发帖失败，请稍后重试'

    if ((err as any).response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      router.push('/login')
    }
  } finally {
    isSubmitting.value = false
  }
}

const goBack = () => {
  router.back()
}
</script>

<style scoped>
.create-post-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 20px;
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.create-post-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 20px 30px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  margin-bottom: 30px;
}

.create-post-header h1 {
  font-size: 28px;
  color: #333;
  margin: 0;
}

.btn-back {
  padding: 8px 20px;
  background: #f8f9fa;
  color: #555;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.3s;
}

.btn-back:hover {
  background: #e9ecef;
}

.create-post-form {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.error-box {
  color: #e74c3c;
  font-weight: 600;
  padding: 12px;
  background: #fee;
  border-radius: 8px;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 25px;
}

.form-group label {
  display: block;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 15px;
  font-family: inherit;
  transition: border-color 0.3s;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
}

.form-group textarea {
  resize: vertical;
  min-height: 200px;
}

.char-count {
  text-align: right;
  font-size: 13px;
  color: #999;
  margin-top: 5px;
}

.form-actions {
  display: flex;
  gap: 15px;
  justify-content: flex-end;
  margin-top: 30px;
}

.btn-submit {
  padding: 12px 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 16px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  padding: 12px 32px;
  background: white;
  color: #555;
  border: 2px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 16px;
  transition: background 0.3s;
}

.btn-cancel:hover {
  background: #f8f9fa;
}
</style>
