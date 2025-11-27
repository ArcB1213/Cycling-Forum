import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../views/LandingPage.vue'

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
  ],
})

export default router
