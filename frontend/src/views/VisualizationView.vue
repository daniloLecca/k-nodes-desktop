<script setup>
    import { ref, onMounted, onUnmounted } from 'vue'
    import { useComplexNetworkStore } from '@/stores/complexNetwork';
    import { getEntireNetworkPositions } from '@/utils/apis';
    import Sigma from 'sigma';
    import Graph from 'graphology';

    const complexNetworkStore = useComplexNetworkStore()
    const containerRef = ref(null)
    const positions = ref(null)
    const sigmaInstance = ref(null)
    let isUnmounted = false

    onMounted(async () => {
        const container = containerRef.value
        if (!(container instanceof HTMLElement)) return

        try {
            positions.value = await getEntireNetworkPositions()
            console.log(positions.value)
            if (isUnmounted || !container.isConnected) return

            const graph = new Graph();
            graph.import(positions.value)

            sigmaInstance.value = new Sigma(graph, container)
        } catch (error) {
            console.error('Failed to initialize Sigma graph:', error)
        }
    })

    onUnmounted(() => {
        isUnmounted = true
        if (sigmaInstance.value) {
            sigmaInstance.value.kill()
            sigmaInstance.value = null
        }
    })
    
</script>

<template>
    <main>
        <div class="title">
            <h2>{{ complexNetworkStore.fileName }}</h2>
            <p>The network has {{ complexNetworkStore.nnodes }} nodes and {{ complexNetworkStore.edges }} edges. </p>
            <p v-if="complexNetworkStore.selfLoops !== 0">
                The network has {{ complexNetworkStore.selfLoops }} self loop(s). Self loops have been removed.
            </p>
        </div>
        <div id="container" ref="containerRef"></div>
    </main>
</template>

<style scoped>

    .title {
        position: absolute;
    }

    main {
        width: 100%;
        margin-top: 2vh;
        background: transparent;
    }

    h1 {
        font-size: 56px;
        font-weight: 500;
    }

    #container {
        height: clamp(900px, 85vh, 100vh);        
    }
</style>