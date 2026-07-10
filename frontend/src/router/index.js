import { createRouter, createWebHashHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import AboutView from '../views/AboutView.vue'
import VisualizationView from '@/views/VisualizationView.vue'
import AnalysisView from '@/views/AnalysisView.vue'
import ResultsView from '@/views/ResultsView.vue'

import { useComplexNetworkStore } from '@/stores/complexNetwork'
import { usePositionsStore } from '@/stores/positionsStore'
import { useComputationStore } from '@/stores/computationStore'
import { deleteNetworkSession } from '@/utils/apis'
import nprogress from 'nprogress'



const router = createRouter({
  history: createWebHashHistory(),
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
    // nprogress.start() -> if loading bar during page navigation is needed 
    const complexNetworkStore = useComplexNetworkStore()
    const computationStore = useComputationStore()
    const positionsStore = usePositionsStore()

    if (to.path === '/') {
      // if the user navigates to the home, the network is deleted
      await deleteNetworkSession()
      positionsStore.currentLayer = {}
      computationStore.computationResult = {}
      computationStore.computationData = {}
      complexNetworkStore.token = ''
    }

    if (to.path === '/results' && computationStore.isComputationDataEmpty) {
      return next({ path: '/'})
    }

    // if no network was uploaded then forbid the navigation 
    if (to.matched.some(r => r.meta.requiresNetwork)) {
      if (!complexNetworkStore.token || typeof complexNetworkStore.token !== 'string' || complexNetworkStore.token.trim() === '') {
              return next({ path: '/'})
          } else {
              return next()
          }
    }

    return next()
})

/* -> if loading bar during page navigation is needed
router.afterEach(() => {
  nprogress.done()
})
  */

export default router
