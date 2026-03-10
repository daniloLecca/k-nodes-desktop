import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useComplexNetworkStore = defineStore('complexNetwork', () => {
  const token = ref('')
  const fileName = ref('')
  const nnodes = ref(0)
  const edges = ref(0)
  const largestEigenvalue = ref(0.0)
  const maxAlpha = ref(0.0)
  const selfLoops = ref(0)
  const clusters = ref({}) // each element has format like { "cluster_id": size }

  return { token, fileName, nnodes, edges, largestEigenvalue, maxAlpha, selfLoops, clusters }
})
