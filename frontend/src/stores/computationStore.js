import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useComputationStore = defineStore('computation', () => {
    const computationResult = ref({})
    const computationData = ref({})

    const isComputationDataEmpty = computed(() => {
        const data = computationData.value

        // null o undefined
        if (!data) return true

        // non è un oggetto (extra sicurezza)
        if (typeof data !== 'object') return true

        // oggetto vuoto
        return Object.keys(data).length === 0
    })

    return { computationResult, computationData, isComputationDataEmpty }
}, { persist: true})