import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useComputationStore = defineStore('computation', () => {
    const vipNodes = ref([])
    const vipScores = ref([])
    const elapsedTime = ref(0.0)

    return { vipNodes, vipScores, elapsedTime}
}, { persist: true})