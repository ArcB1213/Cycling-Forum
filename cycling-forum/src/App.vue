<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <!-- 路由将在这里渲染 -->
  <RouterView />
</template>

<style>
/* 全局样式 (替换 src/assets/base.css 或 main.css) */
body {
  margin: 0;
  font-family:
    Inter,
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    Roboto,
    sans-serif;
  background-color: #f1f5f9; /* slate-100 */
  color: #1e293b; /* slate-800 */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-header {
  background-color: white;
  padding: 1.5rem 0;
  border-bottom: 1px solid #e2e8f0; /* slate-200 */
  margin-bottom: 1.5rem;
  box-shadow:
    0 1px 3px 0 rgb(0 0 0 / 0.1),
    0 1px 2px -1px rgb(0 0 0 / 0.1);
}

.app-header .container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 2rem;
}

.app-header .title {
  font-size: 2.25rem; /* 3xl */
  font-weight: 700;
  margin: 0;
}
.app-header .subtitle {
  font-size: 1.125rem; /* lg */
  color: #64748b; /* slate-500 */
  margin: 0;
}
</style>
