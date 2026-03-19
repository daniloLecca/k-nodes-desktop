<script setup>
    import { ref, onMounted, onBeforeUnmount } from "vue"
    import * as d3 from "d3"
    import { useComplexNetworkStore } from '@/stores/complexNetwork';
    import { useComputationStore } from '@/stores/computationStore';

    const complexNetworkStore = useComplexNetworkStore()
    const computationStore = useComputationStore()

    const props = defineProps({
        title: String,
        description: String, 
        viz: String
    })

    const imageUrl = ref(null)
    const chartContainer = ref(null)
    let resizeObserver = null 

    const usedEigenValues = []
    for (const [key, value] of Object.entries(computationStore.computationResult.candidates_history)) {
        usedEigenValues.push({"i": (parseInt(key) + 1).toString(), "eig": value.eigenvalue})
    }

    console.log(usedEigenValues)


    async function loadPlot() {
    const res = await fetch("/api/plot", {
        method: "POST", 
        headers: {
            "X-Network-token": complexNetworkStore.token
        }
    })

    const blob = await res.blob()
    imageUrl.value = URL.createObjectURL(blob)
    }

    async function loadLineChartEigenvalues() {
        if (!chartContainer.value) {
            return
        }

        const measuredWidth = Math.round(chartContainer.value.getBoundingClientRect().width)
        const outerWidth = measuredWidth > 0 ? measuredWidth : 260
        const outerHeight = outerWidth

        const margin = { top: 12, right: 12, bottom: 28, left: 42 }
        const width = Math.max(10, outerWidth - margin.left - margin.right)
        const height = Math.max(10, outerHeight - margin.top - margin.bottom)

        const container = d3.select(chartContainer.value)
        container.selectAll("*").remove()

        const svg = container
            .append("svg")
            .attr("width", outerWidth)
            .attr("height", outerHeight)
            .attr("viewBox", `0 0 ${outerWidth} ${outerHeight}`)
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`)

        const x = d3.scaleLinear()
            .domain([0, usedEigenValues.length])
            .nice()
            .range([0, width])


        const y = d3.scaleLinear()
            .domain([0, complexNetworkStore.largestEigenvalue])
            .nice()
            .range([height, 0])

        svg.append("g")
            .attr("transform", `translate(0,${height})`)
            .call(d3.axisBottom(x))

        svg.append("g")
            .call(d3.axisLeft(y))

        svg.selectAll("circle")
        .data(usedEigenValues)
        .enter()
        .append("circle")
        .attr("cx", d => x(d.i))
        .attr("cy", d => y(d.eig))
        .attr("r", 2)
        .attr("fill", "none")
        .attr("stroke", "steelblue") .attr("stroke-width", 0.75); 
            
    }

    onMounted(() => {
        if(props.viz === 'scatterplot') {
            loadPlot()
        } else if (props.viz === 'eigenvalues'){
            loadLineChartEigenvalues()

            if (chartContainer.value) {
                resizeObserver = new ResizeObserver(() => {
                    loadLineChartEigenvalues()
                })

                resizeObserver.observe(chartContainer.value)
            }
        }
    })

    onBeforeUnmount(() => {
        if (resizeObserver) {
            resizeObserver.disconnect()
            resizeObserver = null
        }
    })
</script>
<template>
    <main>
        <img v-if="props.viz === 'scatterplot' && imageUrl" :src="imageUrl" class="media-box" />
        <div v-else-if="props.viz === 'eigenvalues'" ref="chartContainer" class="media-box chart-box"></div>
        <article>
            <h3>{{ title }}</h3>
            <p>{{ description }}</p>
        </article>
    </main>
</template>

<style scoped>
    
    main {
        background: var(--color-background-soft);
        border: 1px solid var(--color-border);
        border-radius: 1rem;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        width: 100%;
        display: flex;
        justify-content: flex-start;
        align-items: flex-start;
        gap: 0.75rem;
        margin: 0;
        padding: 0.6rem;
        overflow: hidden;
    }

    article {
        flex: 1 1 auto;
        min-width: 0;
        padding: 0 0 0 1rem;
        margin: 0;
    }

    .media-box {
        display: block;
        flex: 0 0 auto;
        margin: 0;
        width: clamp(140px, 15vw, 260px);
        max-width: 100%;
    }

    img {
        border-radius: 1rem;
        height: auto;
    }

    .chart-box {
        aspect-ratio: 1 / 1;
    }

    @media (max-width: 768px) {
        main {
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        article {
            width: 100%;
            padding: 0;
            text-align: center;
        }

        img {
            margin: 0 auto;
        }
    }
</style>