<script setup>
    import { ref, onMounted, onUnmounted } from 'vue'
    import { useComplexNetworkStore } from '@/stores/complexNetwork';
    import { usePositionsStore } from '@/stores/positionsStore';
    import { useComputationStore } from '@/stores/computationStore';
    import { getEntireNetworkPositions } from '@/utils/apis';
    import Sigma from 'sigma';
    import Graph from 'graphology';
    import nprogress from 'nprogress'

    const complexNetworkStore = useComplexNetworkStore()
    const computationStore = useComputationStore()
    const positions = usePositionsStore()
    const containerRef = ref(null)
    const mainRef = ref(null)
    const sigmaInstance = ref(null)
    const sigmaCamera = ref(null)
    const selectedNodeId = ref(null)
    const isFullscreen = ref(false)
    let graph = null
    let isUnmounted = false

    let draggedNode = null;
    let isDragging = false;

    // ratio = 1 -> default zoom
    // zoom in -> ratio drops
    // zoom out -> ratio rises

    function resetZoom () {
        if (!sigmaCamera.value) return
        sigmaCamera.value.animatedReset({ duration: 600})
        console.log(sigmaCamera.value)
    }

    function zoomIn () {
        if (!sigmaCamera.value) return
        sigmaCamera.value.animatedZoom({ duration: 600})
        console.log(sigmaCamera.value)
    }

    function zoomOut () {
        if (!sigmaCamera.value) return
        sigmaCamera.value.animatedUnzoom({ duration: 600})
        console.log(sigmaCamera.value)
    }

    async function fullScreenMode () {
        const element = mainRef.value
        if (!(element instanceof HTMLElement)) return

        try {
            if (document.fullscreenElement === element) {
                await document.exitFullscreen()
            } else {
                await element.requestFullscreen()
            }
        } catch (error) {
            console.error('Unable to toggle fullscreen mode:', error)
        }
    }

    function handleFullscreenChange() {
        isFullscreen.value = document.fullscreenElement === mainRef.value

        // a refresh after layout size changes is needed (both enter/exit fullscreen).
        if (sigmaInstance.value) {
            sigmaInstance.value.refresh()
        }
    }

    onMounted(async () => {
        document.addEventListener('fullscreenchange', handleFullscreenChange)

        const container = containerRef.value
        if (!(container instanceof HTMLElement)) return

        try {
            // checks if the store is empty, the store is emptied every time the user goes to the home page
            if (!Object.keys(positions.currentLayer).length) {
                nprogress.start()
                positions.currentLayer = await getEntireNetworkPositions()
                nprogress.done()
            }
            console.log(positions.currentLayer)
            if (isUnmounted || !container.isConnected) return

            graph = new Graph();
            graph.import(positions.currentLayer)

            sigmaInstance.value = new Sigma(graph, container, {
                labelRenderedSizeThreshold: 100,
                defaultNodeColor: "yellow"
            })
            sigmaCamera.value = sigmaInstance.value.getCamera()

            sigmaInstance.value.on("downNode", e => {
                isDragging = true
                draggedNode = e.node
                graph.setNodeAttribute(draggedNode, "highlighted", true)
                if (!sigmaInstance.value.getCustomBBox()) sigmaInstance.value.setCustomBBox(sigmaInstance.value.getBBox())
            })

            sigmaInstance.value.on("moveBody", ({ event }) => {
                if (!isDragging || !draggedNode) return;

                const pos = sigmaInstance.value.viewportToGraph(event);

                graph.setNodeAttribute(draggedNode, "x", pos.x);
                graph.setNodeAttribute(draggedNode, "y", pos.y);

                event.preventSigmaDefault();
                event.original.preventDefault();
                event.original.stopPropagation();
            });

            const handleUp = () => {
                if (draggedNode) {
                    graph.removeNodeAttribute(draggedNode, "highlighted");
                }
                isDragging = false;
                draggedNode = null;
            };

            sigmaInstance.value.on("upNode", handleUp);
            sigmaInstance.value.on("upStage", handleUp);

            const vipNodes = Array.isArray(computationStore.computationResult?.vip_nodes)
                ? computationStore.computationResult.vip_nodes
                : []

            // every time the page is loaded, the rendering gets refreshed
            sigmaInstance.value.setSetting("nodeReducer", (nodeId, data) => {
                const isVip = vipNodes.includes(Number(nodeId))
                const isSelected = selectedNodeId.value === nodeId

                const baseLabel = isVip
                    ? "VIP node: " + String(Number(nodeId) + 1)
                    : data.label

                return {
                    ...data,
                    color: isVip ? "orange" : data.color,
                    size: isVip ? 5 : data.size,
                    label: isSelected
                        ? `${baseLabel}, degree: ${graph.degree(nodeId)}`
                        : baseLabel
                }
            })

            sigmaInstance.value.on("clickNode", ({ node }) => {
                selectedNodeId.value = selectedNodeId.value === node ? null : node
                sigmaInstance.value.refresh()
            })
            
            console.log({"nodes":graph.order, "edges": graph.size})
            // the number of edges is half the number of non zero entries in the adjacency matrix

            
        } catch (error) {
            console.error('Failed to initialize Sigma graph:', error)
        }
    })

    onUnmounted(() => {
        isUnmounted = true
        document.removeEventListener('fullscreenchange', handleFullscreenChange)
        if (sigmaInstance.value) {
            sigmaInstance.value.kill()
            sigmaInstance.value = null
        }
    })
    
</script>

<template>
    <main ref="mainRef" :class="{ 'main--fullscreen': isFullscreen }">
        <div class="title">
            <h2>{{ complexNetworkStore.fileName }}</h2>
            <p>The network has {{ complexNetworkStore.nnodes }} nodes and {{ complexNetworkStore.edges }} edges. </p>
            <p v-if="complexNetworkStore.selfLoops !== 0">
                The network has {{ complexNetworkStore.selfLoops }} self loop(s). Self loops have been removed.
            </p>
        </div>
        <div id="container" ref="containerRef"></div>
        <div id="controls">
            <button @click="fullScreenMode()">{{ isFullscreen ? 'x' : '[ ]' }}</button>
            <button @click="zoomIn()">+</button>
            <button @click="zoomOut()">-</button>
            <button @click="resetZoom()">o</button>
        </div>
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

    main:fullscreen,
    .main--fullscreen {
        margin-top: 0;
        width: 100vw;
        height: 100vh;
    }

    h1 {
        font-size: 56px;
        font-weight: 500;
    }

    #container {
        height: 100vh;
    }

    main:fullscreen #container,
    .main--fullscreen #container {
        height: 100vh;
    }

    @media (max-width: 400px) {
        button {
            width: 50%;
        }

        button:first-child {
            visibility: hidden;
        }
    }

    @media (max-height: 999px) {
        #container {
            height: 74vh;   
        }
    }

    @media (min-height: 1000px) {
        #container {
            height: 81vh;   
        }
    }

    #controls {
        position: fixed;
        display: flex;
        flex-direction: column;
        gap: 1rem;
        bottom: 2em;
        right: 1em;
    }

</style>