<template>
  <div class="forum-container">
    <div class="forum-header">
      <h1>📄 帖子详情</h1>
      <div class="header-actions">
        <button @click="goToForum" class="btn-back-forum">← 返回列表</button>
        <button @click="goToCreatePost" class="btn-create">+ 发帖</button>
        <div class="user-info" @click="navigateToProfile">
          <span>{{ user?.nickname }}</span>
          <button @click.stop="handleLogout" class="btn-logout">退出</button>
        </div>
      </div>
    </div>

    <!-- 帖子内容 -->
    <div v-if="isLoading" class="loading">加载中...</div>

    <div v-else-if="error" class="error-box">
      {{ error }}
    </div>

    <div v-else class="forum-content">
      <div class="content-card">
        <h1 class="post-title">{{ post?.title }}</h1>
        <div class="post-meta">
          <div class="post-author">
            <img :src="getAvatarUrl(post?.author_avatar)" class="author-avatar" />
            <span>{{ post?.author_nickname || '未知用户' }}</span>
          </div>
          <div class="post-stats">
            <span>{{ formatDate(post?.created_at || '') }}</span>
            <span>👁 {{ post?.view_count }}</span>
            <span>💬 {{ post?.comment_count }}</span>
          </div>
        </div>
      </div>

      <div class="post-content">
        {{ post?.content }}
      </div>

      <!-- 删除帖子按钮 -->
      <div v-if="isPostAuthor()" class="post-actions">
        <button @click="handleDeletePost" class="btn-delete-post">🗑️ 删除帖子</button>
      </div>

      <!-- 评论区 -->
      <div class="comments-section">
        <div class="comments-header">
          <h2>评论 ({{ comments.length }})</h2>
          <div
            :class="[
              'connection-status',
              wsConnected ? 'connected' : wsConnecting ? 'connecting' : 'disconnected',
            ]"
          >
            <span class="status-dot"></span>
            <span class="status-text">
              {{ wsConnecting ? '连接中...' : wsConnected ? '实时更新已启用' : '离线模式' }}
            </span>
          </div>
        </div>

        <!-- 发表评论 -->
        <div class="comment-form">
          <!-- 回复提示 -->
          <div v-if="replyingTo" class="replying-to">
            <span>正在回复：{{ getReplyingComment()?.author_nickname || '用户' }}</span>
            <button @click="cancelReply" class="btn-cancel-reply">取消</button>
          </div>

          <textarea
            v-model="newComment"
            :placeholder="replyingTo ? '写下你的回复...' : '发表你的看法...'"
            rows="3"
            @keydown.enter.ctrl="submitComment"
            ref="commentTextarea"
          ></textarea>
          <div class="comment-actions">
            <span class="hint">Ctrl + Enter 发送</span>
            <button
              @click="submitComment"
              :disabled="!newComment.trim()"
              class="btn-submit-comment"
            >
              发表评论
            </button>
          </div>
        </div>

        <!-- 评论列表 -->
        <div v-if="isLoadingComments" class="loading-comments">加载评论中...</div>

        <div v-else-if="comments.length === 0" class="empty-comments">暂无评论，快来抢沙发！</div>

        <div v-else class="comments-list">
          <CommentItem
            v-for="comment in comments"
            :key="comment.comment_id"
            :comment="comment"
            :depth="0"
            :current-user-id="currentUser?.user_id"
            @reply="handleReply"
            @delete="handleDeleteComment"
            @refresh="loadComments"
          />
        </div>

        <!-- 分页 -->
        <div v-if="commentPagination.total_pages > 1" class="pagination">
          <button
            :disabled="!commentPagination.has_prev"
            @click="loadCommentsPage(commentPagination.page - 1)"
            class="btn-page"
          >
            上一页
          </button>
          <span class="page-info"
            >第 {{ commentPagination.page }} / {{ commentPagination.total_pages }} 页</span
          >
          <button
            :disabled="!commentPagination.has_next"
            @click="loadCommentsPage(commentPagination.page + 1)"
            class="btn-page"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import '@/assets/forum-styles.css'
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getAvatarUrl,
  fetchForumPostDetail,
  fetchPostComments,
  createComment,
  deleteForumPost,
  deleteComment,
} from '@/services/ApiServices'
import { useWebSocket } from '@/composables/useWebSocket'
import type { ForumPost, ForumComment, PaginationMeta } from '@/interfaces/types'
import CommentItem from '@/components/forum/CommentItem.vue'

const route = useRoute()
const router = useRouter()
const isLoading = ref(true)
const isLoadingComments = ref(false)
const error = ref('')
const post = ref<ForumPost | null>(null)
const comments = ref<ForumComment[]>([])
const newComment = ref('')
const replyingTo = ref<number | null>(null)
const wsConnected = ref(false)
const wsConnecting = ref(false)
const currentUser = ref<any>(null)
const user = ref<any>(null)

const commentPagination = ref<PaginationMeta>({
  total: 0,
  page: 1,
  limit: 20,
  total_pages: 0,
  has_next: false,
  has_prev: false,
})

const formatDate = (dateString: string) => {
  if (!dateString) return '未知'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

const loadPost = async () => {
  try {
    const postId = Number(route.params.postId)
    post.value = await fetchForumPostDetail(postId)
  } catch (err: unknown) {
    console.error('加载帖子失败:', err)
    error.value = '帖子不存在或已被删除'
  } finally {
    isLoading.value = false
  }
}

const loadComments = async (page: number = 1) => {
  isLoadingComments.value = true
  try {
    const postId = Number(route.params.postId)
    const response = await fetchPostComments(postId, page, 20)
    comments.value = response.floors
    commentPagination.value = response.pagination
  } catch (err: unknown) {
    console.error('加载评论失败:', err)
  } finally {
    isLoadingComments.value = false
  }
}

const loadCommentsPage = (page: number) => {
  if (page >= 1 && page <= commentPagination.value.total_pages) {
    loadComments(page)
  }
}

const submitComment = async () => {
  if (!newComment.value.trim()) return

  try {
    const postId = Number(route.params.postId)
    await createComment(postId, {
      content: newComment.value.trim(),
      parent_id: replyingTo.value || undefined,
    })
    newComment.value = ''
    replyingTo.value = null
    // 刷新评论
    loadComments(commentPagination.value.page)
  } catch (err: unknown) {
    console.error('发表评论失败:', err)
    error.value = '发表评论失败，请稍后重试'
  }
}

const handleReply = (commentId: number) => {
  replyingTo.value = commentId
  newComment.value = ''
  // 滚动到评论框
  setTimeout(() => {
    const textarea = document.querySelector('.comment-form textarea') as HTMLTextAreaElement
    textarea?.scrollIntoView({ behavior: 'smooth' })
    textarea?.focus()
  }, 100)
}

const cancelReply = () => {
  replyingTo.value = null
}

// 获取被回复评论的信息
const getReplyingComment = () => {
  if (!replyingTo.value) return null

  // 在一级评论中查找
  let comment = comments.value.find((c) => c.comment_id === replyingTo.value)
  if (comment) return comment

  // 在子回复中递归查找
  const findInChildren = (list: ForumComment[]): ForumComment | null => {
    for (const c of list) {
      if (c.comment_id === replyingTo.value) return c
      if (c.replies?.length) {
        const found = findInChildren(c.replies)
        if (found) return found
      }
    }
    return null
  }

  for (const floor of comments.value) {
    if (floor.replies?.length) {
      const found = findInChildren(floor.replies)
      if (found) return found
    }
  }

  return null
}

// 处理新评论（WebSocket 接收）
const handleNewComment = (newCommentData: ForumComment) => {
  // 如果是子回复（有 parent_id），添加到对应楼层的回复中
  if (newCommentData.parent_id) {
    addReplyToTree(comments.value, newCommentData)
  } else {
    // 一级评论，添加到楼层列表
    comments.value.push(newCommentData)
    commentPagination.value.total += 1
  }
}

// 递归添加回复到树结构
const addReplyToTree = (commentList: ForumComment[], newReply: ForumComment): boolean => {
  for (const comment of commentList) {
    // 如果找到父评论
    if (comment.comment_id === newReply.parent_id) {
      if (!comment.replies) {
        comment.replies = []
      }
      comment.replies.push(newReply)
      return true
    }
    // 递归查找子回复
    if (comment.replies && comment.replies.length > 0) {
      if (addReplyToTree(comment.replies, newReply)) {
        return true
      }
    }
  }
  return false
}

// 删除帖子
const handleDeletePost = async () => {
  if (!confirm('确定要删除这篇帖子吗？删除后无法恢复。')) return

  try {
    const postId = Number(route.params.postId)
    await deleteForumPost(postId)
    alert('帖子已删除')
    router.push('/forum')
  } catch (err: unknown) {
    console.error('删除帖子失败:', err)
    error.value = '删除失败，请稍后重试'
  }
}

// 删除评论
const handleDeleteComment = async (commentId: number) => {
  if (!confirm('确定要删除这条评论吗？删除后无法恢复。')) return

  try {
    const postId = Number(route.params.postId)
    await deleteComment(postId, commentId)
    // 刷新评论列表
    loadComments(commentPagination.value.page)
  } catch (err: unknown) {
    console.error('删除评论失败:', err)
    error.value = '删除失败，请稍后重试'
  }
}

// 检查是否是帖子作者
const isPostAuthor = () => {
  return currentUser.value && post.value && currentUser.value.user_id === post.value.author_id
}

const handleLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
  router.push('/login')
}

const navigateToProfile = () => {
  router.push('/profile')
}

const goToCreatePost = () => {
  router.push('/forum/create')
}

const goToForum = () => {
  router.push('/forum')
}

onMounted(() => {
  // 加载当前用户
  const storedUser = localStorage.getItem('user')
  if (storedUser) {
    currentUser.value = JSON.parse(storedUser)
    user.value = JSON.parse(storedUser)
  }

  loadPost()
  loadComments()

  // 设置 WebSocket 连接
  const postId = Number(route.params.postId)
  const { isConnected, isConnecting, connect, disconnect } = useWebSocket(postId, {
    onMessage: (comment: ForumComment) => {
      handleNewComment(comment)
    },
    onConnected: () => {
      wsConnected.value = true
      wsConnecting.value = false
    },
    onDisconnected: () => {
      wsConnected.value = false
    },
    onError: () => {
      wsConnecting.value = false
    },
  })

  // 暴露连接状态
  watch([isConnected, isConnecting], ([connected, connecting]) => {
    wsConnected.value = connected
    wsConnecting.value = connecting
  })

  // 不需要轮询，评论会实时更新
})
</script>

<style scoped>
/* 帖子特定样式 */

.post-title {
  font-size: 28px;
  color: #333;
  margin: 0 0 20px 0;
  line-height: 1.4;
}

.post-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.post-author {
  display: flex;
  align-items: center;
  gap: 12px;
}

.author-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
}

.post-stats {
  display: flex;
  gap: 20px;
  color: #888;
  font-size: 15px;
}

.post-content {
  white-space: pre-wrap;
  padding: 15px;
  line-height: 1.8;
  color: #333;
  font-size: 16px;
  background-color: rgb(255, 255, 255);
}

.post-actions {
  text-align: right;
  padding-top: 15px;
  border-top: 1px solid #f0f0f0;
  margin-top: 20px;
}

.btn-delete-post {
  padding: 8px 20px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-delete-post:hover {
  background: #c0392b;
  transform: translateY(-2px);
}

.comments-section h2 {
  font-size: 22px;
  color: #333;
  margin: 0;
}

.comments-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.3s;
}

.connection-status.connected {
  background: #d4edda;
  color: #155724;
}

.connection-status.connecting {
  background: #fff3cd;
  color: #856404;
}

.connection-status.disconnected {
  background: #f8d7da;
  color: #721c24;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.connection-status.connected .status-dot {
  background: #28a745;
}

.connection-status.connecting .status-dot {
  background: #ffc107;
  animation: pulse 1s infinite;
}

.connection-status.disconnected .status-dot {
  background: #dc3545;
  animation: none;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.comment-form {
  margin-bottom: 30px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 10px;
}

.replying-to {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #e3f2fd;
  border-left: 4px solid #2196f3;
  border-radius: 6px;
  margin-bottom: 12px;
  font-size: 14px;
  color: #1976d2;
}

.replying-to span {
  font-weight: 600;
}

.btn-cancel-reply {
  padding: 4px 12px;
  background: transparent;
  color: #1976d2;
  border: 1px solid #1976d2;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-cancel-reply:hover {
  background: #1976d2;
  color: white;
}

.comment-form textarea {
  width: 100%;
  padding: 12px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 15px;
  font-family: inherit;
  resize: vertical;
  min-height: 80px;
  box-sizing: border-box;
}

.comment-form textarea:focus {
  outline: none;
  border-color: #667eea;
}

.comment-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}

.hint {
  font-size: 13px;
  color: #999;
}

.btn-submit-comment {
  padding: 10px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: transform 0.2s;
}

.btn-submit-comment:hover:not(:disabled) {
  transform: translateY(-2px);
}

.btn-submit-comment:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-comments,
.empty-comments {
  text-align: center;
  padding: 40px;
  color: #888;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  margin-top: 30px;
}

.btn-page {
  padding: 8px 20px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.btn-page:hover:not(:disabled) {
  background: #5568d3;
}

.btn-page:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.page-info {
  color: #555;
  font-weight: 600;
}
</style>
