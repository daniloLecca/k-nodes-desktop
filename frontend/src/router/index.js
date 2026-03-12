import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import AboutView from '../views/AboutView.vue'
import VisualizationView from '@/views/VisualizationView.vue'
import AnalysisView from '@/views/AnalysisView.vue'
import ResultsView from '@/views/ResultsView.vue'

import { useComplexNetworkStore } from '@/stores/complexNetwork'


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/about',
      name: 'about',
      component: AboutView,
    },
    {
      path: '/overview',
      name: 'overview',
      component: VisualizationView,
      meta: { requiresNetwork: true }
    },
    {
      path: '/analysis',
      name: 'analysis',
      component: AnalysisView,
      meta: { requiresNetwork: true }
    },
    {
      path: '/results',
      name: 'results',
      component: ResultsView,
      meta: { requiresNetwork: true }
    },
  ],
})

/* --------------------  GUARDIA   -------------------- */
router.beforeEach(async (to, _from, next) => {
    const complexNetworkStore = useComplexNetworkStore()
    console.log(complexNetworkStore.token)

    if (to.matched.some(r => r.meta.requiresNetwork)) {

    if (!complexNetworkStore.token || typeof complexNetworkStore.token !== 'string' || complexNetworkStore.token.trim() === '') {
            next({ path: '/'})
        } else {
            next()
        }
    } else {
        next()
    }
})

export default router
