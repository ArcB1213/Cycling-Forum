import { ref, onUnmounted } from 'vue'
import type { ForumComment } from '@/interfaces/types'

interface WebSocketMessage {
  type: 'new_comment'
  data: ForumComment
}

interface UseWebSocketOptions {
  onMessage?: (comment: ForumComment) => void
  onConnected?: () => void
  onDisconnected?: () => void
  onError?: (error: Event) => void
}

export function useWebSocket(postId: number, options: UseWebSocketOptions = {}) {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const isConnecting = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000 // 3 seconds

  // Get WebSocket URL (使用与 API 相同的基础 URL)
  const getWebSocketUrl = () => {
    const token = localStorage.getItem('access_token')
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = '127.0.0.1:8000' // 与 ApiServices.ts 中的 baseURL 保持一致
    return `${protocol}//${host}/ws/forum/posts/${postId}/comments?token=${token}`
  }

  // Connect to WebSocket
  const connect = () => {
    if (ws.value?.readyState === WebSocket.OPEN) {
      return
    }

    isConnecting.value = true

    try {
      ws.value = new WebSocket(getWebSocketUrl())

      ws.value.onopen = () => {
        isConnected.value = true
        isConnecting.value = false
        reconnectAttempts.value = 0
        options.onConnected?.()
        console.log('WebSocket connected')
      }

      ws.value.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)

          // Handle heartbeat
          if (event.data === 'pong') {
            return
          }

          if (message.type === 'new_comment') {
            options.onMessage?.(message.data)
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.value.onerror = (error) => {
        console.error('WebSocket error:', error)
        options.onError?.(error)
      }

      ws.value.onclose = () => {
        isConnected.value = false
        isConnecting.value = false
        options.onDisconnected?.()
        console.log('WebSocket disconnected')

        // Attempt to reconnect
        if (reconnectAttempts.value < maxReconnectAttempts) {
          reconnectAttempts.value++
          console.log(`Reconnecting... Attempt ${reconnectAttempts.value}/${maxReconnectAttempts}`)
          setTimeout(connect, reconnectDelay)
        } else {
          console.error('Max reconnect attempts reached')
        }
      }
    } catch (error) {
      isConnecting.value = false
      console.error('Failed to create WebSocket connection:', error)
      options.onError?.(error as Event)
    }
  }

  // Disconnect WebSocket
  const disconnect = () => {
    if (ws.value) {
      reconnectAttempts.value = maxReconnectAttempts // Prevent auto-reconnect
      ws.value.close()
      ws.value = null
      isConnected.value = false
    }
  }

  // Send heartbeat to keep connection alive
  const startHeartbeat = () => {
    const heartbeatInterval = setInterval(() => {
      if (ws.value?.readyState === WebSocket.OPEN) {
        ws.value.send('ping')
      } else {
        clearInterval(heartbeatInterval)
      }
    }, 30000) // Every 30 seconds

    // Clear interval on unmount
    onUnmounted(() => {
      clearInterval(heartbeatInterval)
    })
  }

  // Auto-connect on mount
  connect()
  startHeartbeat()

  // Auto-disconnect on unmount
  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    isConnecting,
    connect,
    disconnect
  }
}
