import { ref } from 'vue'
import { defineStore } from 'pinia'

export const usePositionsStore = defineStore('positions', () => {
  const currentLayer = ref({})

  return { currentLayer }
},
 {
  persist: true,
})
