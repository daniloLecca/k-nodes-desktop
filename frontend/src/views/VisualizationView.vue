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
    const loadingState = ref('')
    const nodeToZoom = ref(1)
    const displayNodeSearchBar = ref(false)
    let previousBodyOverflow = ''
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
    }

    function zoomIn () {
        if (!sigmaCamera.value) return
        sigmaCamera.value.animatedZoom({ duration: 600})
    }

    function zoomOut () {
        if (!sigmaCamera.value) return
        sigmaCamera.value.animatedUnzoom({ duration: 600})
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

    function showNodeSearchBar () {
        displayNodeSearchBar.value = !displayNodeSearchBar.value
    }

    function searchNode () {
        if (!sigmaCamera.value || !sigmaInstance.value || !graph) return

        const nodeId = String(Number(nodeToZoom.value) - 1)
        if (!graph.hasNode(nodeId)) return

        const displayData = sigmaInstance.value.getNodeDisplayData(nodeId)
        const coords = displayData
            ? { x: displayData.x, y: displayData.y }
            : graph.getNodeAttributes(nodeId)

        const target = { x: coords.x, y: coords.y, ratio: 0.01 }

        sigmaCamera.value.animate(target, {
            duration: 700,
            onComplete: () => sigmaCamera.value.setState(target)
        })

        selectedNodeId.value = nodeId
        sigmaInstance.value.refresh({ skipIndexation: true })
    }
    onMounted(async () => {
        const container = containerRef.value
        const TRICKLE_COEFFICIENT = 10 // used for loading bar progress
        // to avoid scroolbar 
        previousBodyOverflow = document.body.style.overflow
        document.body.style.overflow = 'hidden'
        nprogress.configure({
            showSpinner: true,
            minimum: 0.08,
            trickleSpeed: complexNetworkStore.nnodes / TRICKLE_COEFFICIENT, 
            trickleRate: 0.02
        })
        document.addEventListener('fullscreenchange', handleFullscreenChange)

        if (!(container instanceof HTMLElement)) return

        try {
            // checks if the store is empty, the store is emptied every time the user goes to the home page
            if (!Object.keys(positions.currentLayer).length) {
                nprogress.start()
                loadingState.value = 'Loading visualization...'
                positions.currentLayer = await getEntireNetworkPositions()
                loadingState.value = ''
                nprogress.done()
            }
            if (isUnmounted || !container.isConnected) return

            graph = new Graph();
            graph.import(positions.currentLayer)

            const nodeDegrees = new Map()
            graph.forEachNode((nodeId) => {
              nodeDegrees.set(nodeId, graph.degree(nodeId))
            })

            sigmaInstance.value = new Sigma(graph, container, {
                labelRenderedSizeThreshold: 100,
                defaultNodeColor: "yellow", 
                zIndex: true, 
            })
            sigmaCamera.value = sigmaInstance.value.getCamera()

            // check if node is being clicked 
            sigmaInstance.value.on("downNode", e => {
                isDragging = true
                draggedNode = e.node
                graph.setNodeAttribute(draggedNode, "highlighted", true)
                if (!sigmaInstance.value.getCustomBBox()) sigmaInstance.value.setCustomBBox(sigmaInstance.value.getBBox())
            })

            // node dragging
            sigmaInstance.value.on("moveBody", ({ event }) => {
                if (!isDragging || !draggedNode) return;
                
                sigmaInstance.value?.setCustomBBox(null)

                const pos = sigmaInstance.value.viewportToGraph(event);

                graph.setNodeAttribute(draggedNode, "x", pos.x);
                graph.setNodeAttribute(draggedNode, "y", pos.y);

                event.preventSigmaDefault();
                event.original.preventDefault();
                event.original.stopPropagation();
            });

            // node release
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
            // make orange the VIP nodes and update their labels
            sigmaInstance.value.setSetting("nodeReducer", (nodeId, data) => {
                const isVip = vipNodes.includes(Number(nodeId))
                const isSelected = selectedNodeId.value === nodeId
                const degree = nodeDegrees.get(nodeId) ?? 0

                const baseLabel = isVip
                    ? "VIP node: " + String(Number(nodeId) + 1)
                    : data.label

                return {
                    ...data,
                    color: isVip ? "orange" : data.color,
                    size: isVip ? 5 : data.size,
                    zIndex: isVip ? 9999 : 1,
                    label: isSelected
                        ? `${baseLabel}, degree: ${degree}`
                        : baseLabel
                }
            })

            // when another node is clicked the previous clicked node doesn't show its degree
            sigmaInstance.value.on("clickNode", ({ node }) => {
                selectedNodeId.value = selectedNodeId.value === node ? null : node
                
                sigmaInstance.value.refresh({ skipIndexation: true })
            })
            
            console.log({"nodes":graph.order, "edges": graph.size})
            // the number of edges is half the number of non zero entries in the adjacency matrix

            
        } catch (error) {
            console.error('Failed to initialize Sigma graph:', error)
        }
    })

    onUnmounted(() => {
        isUnmounted = true
        document.body.style.overflow = previousBodyOverflow
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
            <p><i>{{ loadingState }}</i></p>
        </div>
        <div class="node-search-bar" v-if="displayNodeSearchBar">
            <input type="number" name="nodeToZoom" id="nodeToZoom" autofocus v-model="nodeToZoom" min="1" :max="complexNetworkStore.nnodes" @keypress.enter="searchNode()">
        </div>
        <div id="container" ref="containerRef" @click="displayNodeSearchBar = false"></div>
        <div id="controls">
            <button @click="fullScreenMode()">
                <svg v-if="!isFullscreen" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <g stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M8 3 H5 Q3 3 3 5 V8"/>
                        <path d="M16 3 H19 Q21 3 21 5 V8"/>
                        <path d="M21 16 V19 Q21 21 19 21 H16"/>
                        <path d="M8 21 H5 Q3 21 3 19 V16"/>
                    </g>
                </svg>
                <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <g stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M10 7 H7 Q6 7 6 8 V10"/>
                        <path d="M14 7 H17 Q18 7 18 8 V10"/>
                        <path d="M18 14 V17 Q18 18 17 18 H14"/>
                        <path d="M10 18 H7 Q6 18 6 17 V14"/>
                    </g>
                </svg>
            </button>
            <button @click="showNodeSearchBar()">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="7"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
            </button>
            <button @click="zoomIn()">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="7"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    <line x1="11" y1="8" x2="11" y2="14"/>
                    <line x1="8" y1="11" x2="14" y2="11"/>
                </svg>
            </button>
            <button @click="zoomOut()">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="7"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    <line x1="8" y1="11" x2="14" y2="11"/>
                </svg>
            </button>
            <button @click="resetZoom()">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="7" stroke="currentColor" stroke-width="2"/>
                    <g stroke="currentColor" stroke-width="1" stroke-linecap="round">
                        <line x1="12" y1="2.5" x2="12" y2="5"/>
                        <line x1="12" y1="19" x2="12" y2="21.5"/>
                        <line x1="2.5" y1="12" x2="5" y2="12"/>
                        <line x1="19" y1="12" x2="21.5" y2="12"/>
                    </g>
                    <circle cx="12" cy="12" r="2.2" fill="currentColor"/>
                </svg>
            </button>
        </div>
    </main>
</template>

<style scoped>

    .title {
        position: absolute;
    }

    main {
        width: 100%;
        margin-top: 0;
        height: 83vh;
        overflow: hidden;
        background: transparent;
    }

    main:fullscreen,
    .main--fullscreen {
        margin-top: 0;
        width: 100vw;
        height: 100vh;
        background: var(--color-background);
    }

    :global(main:fullscreen::backdrop) {
        background: var(--color-background);
    }

    h1 {
        font-size: 56px;
        font-weight: 500;
    }

    button {
        color: var(--color-background);
    }

    .node-search-bar {
        position: absolute;
        top: 2rem;
        right: 20vh;
        height: 5vh;
        width: 25vh;
        background-color: var(--color-background);
        z-index: 9999;
    }

    .node-search-bar input {
        width: 85%;
        border: 1px solid var(--color-border);
        border-radius: 0.6rem;
        background: var(--color-background);
        color: var(--color-text);
        padding: 0.55rem 0.7rem;
        font-family: inherit;
        font-size: 1rem;
    }

    #container {
        height: 100%;
    }

    main:fullscreen #container,
    .main--fullscreen #container {
        height: 100vh;
    }

    main:fullscreen .node-search-bar,
    .main--fullscreen .node-search-bar {
        background: transparent;
    }

    @media (max-width: 441px) {
        .node-search-bar {
            width: 83%;
            left: 10%;
            top: 1.5rem;
        }

        button {
            width: 85%;
        }

        main {
            height: 76vh;
        }

        button:first-child {
            visibility: hidden;
        }

        svg {
            width: 100%;
            height: 100%;
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