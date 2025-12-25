<template>
  <div class="action-card">
    <div class="tabs-header">
      <button
        :class="['tab-button', { active: activeTab === 'ratings' }]"
        @click="$emit('switch-tab', 'ratings')"
      >
        🏆 {{ isOwner ? '我的评价' : 'TA的评价' }}
      </button>
      <button
        :class="['tab-button', { active: activeTab === 'posts' }]"
        @click="$emit('switch-tab', 'posts')"
      >
        📝 {{ isOwner ? '我的帖子' : 'TA的帖子' }}
      </button>
    </div>

    <div class="tab-content">
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  activeTab: 'ratings' | 'posts'
  isOwner: boolean
}

defineProps<Props>()

defineEmits<{
  'switch-tab': [tab: 'ratings' | 'posts']
}>()
</script>

<style scoped>
.action-card {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.tabs-header {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  border-bottom: 2px solid #f0f0f0;
}

.tab-button {
  padding: 12px 24px;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  font-size: 16px;
  font-weight: 600;
  color: #666;
  cursor: pointer;
  transition: all 0.3s;
}

.tab-button:hover {
  color: #333;
}

.tab-button.active {
  color: #ff286e;
  border-bottom-color: #ff286e;
}

.tab-content {
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
