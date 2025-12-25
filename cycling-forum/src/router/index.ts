import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../views/LandingPage.vue'
import apiService from '@/services/ApiServices'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: LandingPage,
    },
    {
      path: '/races',
      name: 'races',
      component: () => import('../views/RacesView.vue'),
    },
    {
      path: '/riders',
      name: 'riders',
      component: () => import('../views/RidersView.vue'),
    },
    {
      path: '/riders/:id',
      name: 'rider-detail',
      component: () => import('../views/RiderDetailView.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { guest: true }, // 仅未登录用户可访问
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { guest: true }, // 仅未登录用户可访问
    },
    {
      path: '/verify-email',
      name: 'verify-email',
      component: () => import('../views/VerifyEmailView.vue'),
    },
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: () => import('../views/ForgotPasswordView.vue'),
      meta: { guest: true },
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: () => import('../views/ResetPasswordView.vue'),
      meta: { guest: true },
    },
    {
      path: '/forum',
      name: 'forum',
      component: () => import('../views/ForumView.vue'),
      meta: { requiresAuth: true }, // 需要登录
    },
    {
      path: '/forum/create',
      name: 'create-post',
      component: () => import('../views/CreatePostView.vue'),
      meta: { requiresAuth: true }, // 需要登录
    },
    {
      path: '/forum/post/:postId',
      name: 'post-detail',
      component: () => import('../views/PostDetailView.vue'),
      meta: { requiresAuth: true }, // 需要登录
    },
    {
      path: '/profile/:userId?',
      name: 'profile',
      component: () => import('../views/UserProfileView.vue'),
      meta: { requiresAuth: true }, // 需要登录
    },
  ],
})

// 路由守卫：保护需要认证的路由
router.beforeEach((to, from, next) => {
  const isAuthenticated = apiService.isAuthenticated()

  // 如果路由需要认证但用户未登录
  if (to.meta.requiresAuth && !isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } })
  }
  // 如果路由仅允许访客访问但用户已登录
  else if (to.meta.guest && isAuthenticated) {
    next({ name: 'landing' })
  }
  // 正常通过
  else {
    next()
  }
})

export default router
