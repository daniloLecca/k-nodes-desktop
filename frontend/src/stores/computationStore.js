import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useComputationStore = defineStore('computation', () => {
    const computationResult = ref({})
    const computationData = ref({})

    return { computationResult, computationData }
}, { persist: true})